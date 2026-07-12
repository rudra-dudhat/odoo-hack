import pytest
from pydantic import ValidationError
from datetime import datetime, timezone
from src.domain.entities.employee import Employee
from src.domain.entities.department import Department
from src.domain.enums import EmployeeStatus, DepartmentStatus
from src.domain.value_objects.snapshots import DepartmentSnapshot, RoleSnapshot
from src.application.dtos.employees import EmployeeCreate

def test_department_serialization_camel_case():
    dept = Department(
        id="dept_123",
        name="Engineering",
        code="ENG",
        description="Software development department",
        status=DepartmentStatus.ACTIVE,
        employee_count=5,
        asset_count=10,
        head_employee_id="uid_abc",
        created_by="system",
        updated_by="system"
    )
    
    dumped = dept.model_dump(by_alias=True)
    assert dumped["employeeCount"] == 5
    assert dumped["assetCount"] == 10
    assert dumped["headEmployeeId"] == "uid_abc"
    assert "id" in dumped

def test_employee_validation_rules():
    # Test valid creation using Employee entity
    emp = Employee(
        id="uid_123",
        full_name="Akshay Kumar",
        email="akshay@company.com",
        phone="+15555551212",
        avatar_url="http://avatar.url/image.png",
        department_id="dept_abc",
        department_snapshot=DepartmentSnapshot(name="Engineering", code="ENG"),
        role_id="role_manager",
        role_snapshot=RoleSnapshot(name="Manager"),
        designation="Manager of Engineering",
        employee_code="EMP-000001",
        join_date=datetime.now(timezone.utc),
        status=EmployeeStatus.ACTIVE,
        created_by="system",
        updated_by="system"
    )
    assert emp.full_name == "Akshay Kumar"
    
    # Test invalid email format validation on EmployeeCreate DTO
    with pytest.raises(ValidationError):
        EmployeeCreate(
            uid="uid_123",
            fullName="Akshay Kumar",
            email="invalid_email",
            phone="+15555551212",
            departmentId="dept_abc",
            roleId="role_manager",
            designation="Manager",
            joinDate=datetime.now(timezone.utc)
        )
        
    # Test invalid phone number format validation on EmployeeCreate DTO
    with pytest.raises(ValidationError):
        EmployeeCreate(
            uid="uid_123",
            fullName="Akshay Kumar",
            email="akshay@company.com",
            phone="123-invalid-phone", # invalid phone pattern containing letters
            departmentId="dept_abc",
            roleId="role_manager",
            designation="Manager",
            joinDate=datetime.now(timezone.utc)
        )
