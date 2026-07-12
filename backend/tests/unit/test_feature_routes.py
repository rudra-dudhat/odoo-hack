import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.presentation.api.v1 import dashboard as dashboard_module


class FakeDoc:
    def __init__(self, data, doc_id):
        self._data = data
        self.id = doc_id

    def to_dict(self):
        return self._data


class FakeCollection:
    def __init__(self, docs):
        self._docs = docs

    def stream(self):
        return [FakeDoc(doc, doc.get("id", f"doc-{idx}")) for idx, doc in enumerate(self._docs)]


class FakeDb:
    def __init__(self, collections):
        self._collections = collections

    def collection(self, name):
        return FakeCollection(self._collections.get(name, []))


@pytest.fixture
def dashboard_client(monkeypatch):
    fake_db = FakeDb(
        {
            "assets": [{"id": "AST-001", "isDeleted": False}, {"id": "AST-002", "isDeleted": True}],
            "assetAllocations": [{"id": "ALLOC-001", "status": "active"}, {"id": "ALLOC-002", "status": "overdue"}],
            "resourceBookings": [{"id": "BK-001", "status": "confirmed"}],
            "maintenanceRequests": [{"id": "MAINT-001", "status": "pending"}],
        }
    )
    monkeypatch.setattr(dashboard_module, "db", fake_db)

    app = FastAPI()
    app.include_router(dashboard_module.router, prefix="/api/v1/dashboard")
    return TestClient(app)


def test_dashboard_summary_uses_firestore_collections(dashboard_client):
    response = dashboard_client.get("/api/v1/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["totalAssets"] == 1
    assert payload["activeAllocations"] == 1
    assert payload["overdueAllocations"] == 1
    assert payload["bookingsToday"] == 1
    assert payload["openMaintenanceRequests"] == 1
