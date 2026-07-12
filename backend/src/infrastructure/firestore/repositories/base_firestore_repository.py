import base64
import json
from datetime import datetime
from typing import Any, TypeVar, Generic
from google.cloud import firestore
from src.domain.repositories.base_repository import BaseRepository
from src.infrastructure.firestore.client import db
from src.shared.errors import NotFoundError, ConflictError
from src.shared.logging import logger

T = TypeVar("T")

def serialize_cursor(sort_value: Any, doc_id: str) -> str:
    """Base64 encode pagination cursor values."""
    if isinstance(sort_value, datetime):
        val = {"__type__": "datetime", "val": sort_value.isoformat()}
    else:
        val = sort_value
        
    data = [val, doc_id]
    json_bytes = json.dumps(data).encode("utf-8")
    return base64.urlsafe_b64encode(json_bytes).decode("utf-8")

def deserialize_cursor(cursor_str: str) -> tuple[Any, str]:
    """Decode and deserialize a cursor string."""
    try:
        json_bytes = base64.urlsafe_b64decode(cursor_str.encode("utf-8"))
        data = json.loads(json_bytes.decode("utf-8"))
        val, doc_id = data[0], data[1]
        
        if isinstance(val, dict) and val.get("__type__") == "datetime":
            # Strip trailing Z/offset if present for python parser consistency
            dt_str = val["val"].replace("Z", "+00:00")
            val = datetime.fromisoformat(dt_str)
            
        return val, doc_id
    except Exception as e:
        logger.error(f"Failed to deserialize cursor: {e}")
        raise ValueError("Invalid cursor parameter")

class BaseFirestoreRepository(BaseRepository[T], Generic[T]):
    def __init__(self, collection_name: str, entity_class: Any):
        self.collection_name = collection_name
        self.entity_class = entity_class
        self._collection_ref = db.collection(collection_name)

    def get_by_id(self, doc_id: str) -> T | None:
        try:
            doc_ref = self._collection_ref.document(doc_id)
            snapshot = doc_ref.get()
            if not snapshot.exists:
                return None
                
            data = snapshot.to_dict() or {}
            data["id"] = snapshot.id
            return self.entity_class.model_validate(data)
        except Exception as e:
            logger.error(f"Error fetching from {self.collection_name}/{doc_id}: {e}")
            raise e

    def list(
        self,
        limit: int = 25,
        cursor: str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "asc",
        filters: dict[str, Any] | None = None,
        include_deleted: bool = False
    ) -> tuple[list[T], str | None]:
        try:
            query = self._collection_ref
            
            # Apply soft-delete filter
            if not include_deleted:
                query = query.where("isDeleted", "==", False)
                
            # Apply other filters
            if filters:
                for field, val in filters.items():
                    # Handle None or standard equality
                    query = query.where(field, "==", val)
                    
            # Handle sorting
            # Default sort if not specified
            primary_sort = sort_by or "createdAt"
            direction = firestore.Query.ASCENDING if sort_dir == "asc" else firestore.Query.DESCENDING
            
            query = query.order_by(primary_sort, direction=direction)
            # Ensure deterministic sorting with doc ID secondary sorting
            if primary_sort != "__name__":
                query = query.order_by("__name__", direction=direction)
                
            # Apply cursor-based pagination
            if cursor:
                sort_val, doc_id = deserialize_cursor(cursor)
                # If primary_sort is "__name__", we only pass the doc_id to start_after
                if primary_sort == "__name__":
                    query = query.start_after((doc_id,))
                else:
                    query = query.start_after((sort_val, doc_id))
                    
            # Fetch limit + 1 to check if there is a next page
            query = query.limit(limit + 1)
            snapshots = query.get()
            
            items = []
            has_more = len(snapshots) > limit
            results_to_return = snapshots[:limit]
            
            for snap in results_to_return:
                data = snap.to_dict() or {}
                data["id"] = snap.id
                items.append(self.entity_class.model_validate(data))
                
            next_cursor = None
            if has_more and results_to_return:
                last_snap = results_to_return[-1]
                last_data = last_snap.to_dict() or {}
                
                # Get the sort value of the last document
                if primary_sort == "__name__":
                    last_sort_val = last_snap.id
                else:
                    # Retrieve the raw field value from the dict representation
                    # Convert python snake_case query sorting to camelCase if needed,
                    # but the incoming sort_by parameter from presentation layer should match camelCase.
                    last_sort_val = last_data.get(primary_sort)
                    
                next_cursor = serialize_cursor(last_sort_val, last_snap.id)
                
            return items, next_cursor
            
        except Exception as e:
            logger.error(f"Error listing collection {self.collection_name}: {e}")
            raise e

    def create(self, entity: T) -> T:
        try:
            # We assume the entity has an 'id' attribute that may be None or a string
            doc_id = getattr(entity, "id", None)
            
            # Entities use standard audit fields which are initialized at service layer
            # Serialize the entity to a dict using camelCase aliases
            entity_dict = entity.model_dump(by_alias=True, exclude_none=True)
            entity_dict.pop("id", None) # Do not write ID inside document fields
            
            # Timestamp stamp fields
            entity_dict["createdAt"] = firestore.SERVER_TIMESTAMP
            entity_dict["updatedAt"] = firestore.SERVER_TIMESTAMP
            
            if doc_id:
                doc_ref = self._collection_ref.document(doc_id)
                # Read check inside a transaction is typically handled in service layer. 
                # Here we do a standard check
                if doc_ref.get().exists:
                    raise ConflictError(f"Document with ID {doc_id} already exists in {self.collection_name}")
                doc_ref.set(entity_dict)
            else:
                # Firestore auto-id generation
                doc_ref = self._collection_ref.document()
                doc_id = doc_ref.id
                doc_ref.set(entity_dict)
                
            # Read back created entity
            created_snap = doc_ref.get()
            created_data = created_snap.to_dict() or {}
            created_data["id"] = doc_id
            return self.entity_class.model_validate(created_data)
            
        except ConflictError as e:
            raise e
        except Exception as e:
            logger.error(f"Error creating in {self.collection_name}: {e}")
            raise e

    def update(self, doc_id: str, updates: dict[str, Any], updated_by: str) -> T:
        try:
            doc_ref = self._collection_ref.document(doc_id)
            if not doc_ref.get().exists:
                raise NotFoundError(f"Document {doc_id} not found in {self.collection_name}")
                
            # Perform field merge update
            # We must map updates to camelCase aliases if they are passed as snake_case,
            # but usually the service layer maps DTOs to raw camelCase dictionaries.
            # Let's ensure updates has the correct actor stamps
            updates["updatedAt"] = firestore.SERVER_TIMESTAMP
            updates["updatedBy"] = updated_by
            
            doc_ref.update(updates)
            
            # Read back updated document
            snap = doc_ref.get()
            data = snap.to_dict() or {}
            data["id"] = snap.id
            return self.entity_class.model_validate(data)
            
        except NotFoundError as e:
            raise e
        except Exception as e:
            logger.error(f"Error updating {self.collection_name}/{doc_id}: {e}")
            raise e

    def soft_delete(self, doc_id: str, deleted_by: str) -> None:
        try:
            doc_ref = self._collection_ref.document(doc_id)
            if not doc_ref.get().exists:
                raise NotFoundError(f"Document {doc_id} not found in {self.collection_name}")
                
            updates = {
                "isDeleted": True,
                "deletedAt": firestore.SERVER_TIMESTAMP,
                "deletedBy": deleted_by,
                "updatedAt": firestore.SERVER_TIMESTAMP,
                "updatedBy": deleted_by
            }
            doc_ref.update(updates)
        except NotFoundError as e:
            raise e
        except Exception as e:
            logger.error(f"Error soft deleting {self.collection_name}/{doc_id}: {e}")
            raise e

    def restore(self, doc_id: str) -> None:
        try:
            doc_ref = self._collection_ref.document(doc_id)
            if not doc_ref.get().exists:
                raise NotFoundError(f"Document {doc_id} not found in {self.collection_name}")
                
            updates = {
                "isDeleted": False,
                "deletedAt": None,
                "deletedBy": None,
                "updatedAt": firestore.SERVER_TIMESTAMP
            }
            doc_ref.update(updates)
        except NotFoundError as e:
            raise e
        except Exception as e:
            logger.error(f"Error restoring {self.collection_name}/{doc_id}: {e}")
            raise e

    def hard_delete(self, doc_id: str) -> None:
        try:
            doc_ref = self._collection_ref.document(doc_id)
            doc_ref.delete()
        except Exception as e:
            logger.error(f"Error hard deleting {self.collection_name}/{doc_id}: {e}")
            raise e
