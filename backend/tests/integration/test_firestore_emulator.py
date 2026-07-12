import tests.conftest
import os
import socket
import pytest
from unittest.mock import MagicMock
from src.infrastructure.firestore.client import db
from src.infrastructure.firestore.repositories.firestore_department_repository import FirestoreDepartmentRepository
from src.domain.entities.department import Department
from src.domain.enums import DepartmentStatus

def is_emulator_running(host="localhost", port=8080) -> bool:
    try:
        # Resolve address and attempt short-timeout socket connection
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

# Determine if we should mock or run against live emulator
USING_EMULATOR = os.getenv("FIRESTORE_EMULATOR_HOST") is not None and is_emulator_running()

def test_department_repository_crud(mocker):
    repo = FirestoreDepartmentRepository()
    
    if USING_EMULATOR:
        # Live emulator test
        # Clear/Setup unique test doc
        dept_id = "test_dept_integration_123"
        repo.hard_delete(dept_id)
        
        dept = Department(
            id=dept_id,
            name="Testing Integration",
            code="TINT",
            description="Integration test category",
            status=DepartmentStatus.ACTIVE,
            created_by="tester",
            updated_by="tester"
        )
        
        # Create
        created = repo.create(dept)
        assert created.id == dept_id
        assert created.code == "TINT"
        
        # Get
        fetched = repo.get_by_id(dept_id)
        assert fetched is not None
        assert fetched.name == "Testing Integration"
        
        # Update
        updated = repo.update(dept_id, {"description": "Updated Description"}, "updater")
        assert updated.description == "Updated Description"
        
        # Soft Delete
        repo.soft_delete(dept_id, "deleter")
        fetched_after_delete = repo.get_by_id(dept_id)
        assert fetched_after_delete.is_deleted is True
        
        # Restore
        repo.restore(dept_id)
        assert repo.get_by_id(dept_id).is_deleted is False
        
        # Clean up
        repo.hard_delete(dept_id)
        
    else:
        # Mock-based fallback verification (Mocking Firestore library structures)
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.id = "mock_dept_123"
        mock_doc.to_dict.return_value = {
            "name": "Mock Department",
            "code": "MOCK",
            "description": "Mocked",
            "status": "active",
            "createdBy": "tester",
            "updatedBy": "tester",
            "isDeleted": False
        }
        
        # Mock collection ref and doc ref calls
        mock_col = MagicMock()
        mock_col.document.return_value.get.return_value = mock_doc
        mocker.patch.object(repo, "_collection_ref", mock_col)
        
        fetched = repo.get_by_id("mock_dept_123")
        assert fetched is not None
        assert fetched.name == "Mock Department"
        assert fetched.code == "MOCK"
        
        # Verify document call was made
        repo._collection_ref.document.assert_called_with("mock_dept_123")
