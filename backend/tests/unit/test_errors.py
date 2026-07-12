from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.shared.errors import NotFoundError, ConflictError, ValidationError, ForbiddenError, UnauthenticatedError
from src.presentation.middleware.error_handler import setup_exception_handlers

def test_error_handlers_mapping():
    # Setup test FastAPI app
    app = FastAPI()
    setup_exception_handlers(app)
    
    @app.get("/not-found")
    def raise_not_found():
        raise NotFoundError("Resource not found message")
        
    @app.get("/conflict")
    def raise_conflict():
        raise ConflictError("Conflict occurred")
        
    @app.get("/validation")
    def raise_validation():
        raise ValidationError("Input invalid")
        
    @app.get("/unauthenticated")
    def raise_unauth():
        raise UnauthenticatedError("Login required")
        
    @app.get("/forbidden")
    def raise_forb():
        raise ForbiddenError("Permission denied")

    client = TestClient(app)
    
    # Test 404
    r = client.get("/not-found")
    assert r.status_code == 404
    assert r.json() == {
        "success": False,
        "error": {
            "code": "NOT_FOUND",
            "message": "Resource not found message",
            "fieldErrors": []
        }
    }
    
    # Test 409
    r = client.get("/conflict")
    assert r.status_code == 409
    assert r.json() == {
        "success": False,
        "error": {
            "code": "CONFLICT",
            "message": "Conflict occurred",
            "fieldErrors": []
        }
    }
    
    # Test 400
    r = client.get("/validation")
    assert r.status_code == 400
    assert r.json() == {
        "success": False,
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Input invalid",
            "fieldErrors": []
        }
    }
    
    # Test 401
    r = client.get("/unauthenticated")
    assert r.status_code == 401
    assert r.json() == {
        "success": False,
        "error": {
            "code": "UNAUTHENTICATED",
            "message": "Login required",
            "fieldErrors": []
        }
    }
    
    # Test 403
    r = client.get("/forbidden")
    assert r.status_code == 403
    assert r.json() == {
        "success": False,
        "error": {
            "code": "FORBIDDEN",
            "message": "Permission denied",
            "fieldErrors": []
        }
    }
