import tests.conftest
import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.presentation.dependencies.auth import get_current_employee
from src.presentation.dependencies.rbac import require_permission
from src.domain.entities.employee import Employee
from src.domain.enums import EmployeeStatus
from src.domain.value_objects.snapshots import DepartmentSnapshot, RoleSnapshot

# 1. Setup a dummy authenticated user fixture
dummy_employee = Employee(
    id="uid_tester_123",
    full_name="Tester Employee",
    email="tester@company.com",
    phone="+15555551212",
    avatar_url=None,
    department_id="dept_test",
    department_snapshot=DepartmentSnapshot(name="QA Testing", code="QA"),
    role_id="role_admin",  # Admin role gives us permissions
    role_snapshot=RoleSnapshot(name="Administrator"),
    designation="Quality Engineer",
    employee_code="EMP-999999",
    join_date="2026-01-01T00:00:00Z",
    status=EmployeeStatus.ACTIVE,
    created_by="system",
    updated_by="system"
)

async def override_get_current_employee() -> Employee:
    return dummy_employee

async def override_require_permission_view() -> Employee:
    return dummy_employee

def test_health_check():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy", "service": "erp-backend"}

def test_get_current_employee_profile_override():
    # Apply dependency overrides
    app.dependency_overrides[get_current_employee] = override_get_current_employee
    
    client = TestClient(app)
    r = client.get("/api/v1/employees/me")
    
    assert r.status_code == 200
    assert r.json()["success"] is True
    assert r.json()["data"]["fullName"] == "Tester Employee"
    assert r.json()["data"]["email"] == "tester@company.com"
    
    # Clean up overrides
    app.dependency_overrides.clear()

def test_unauthenticated_request():
    client = TestClient(app)
    # Call a route that requires auth without header or override
    r = client.get("/api/v1/employees/me")
    assert r.status_code == 401
    assert r.json()["success"] is False
    assert r.json()["error"]["code"] == "UNAUTHENTICATED"
