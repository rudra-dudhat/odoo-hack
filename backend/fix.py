import os

base_dir = "src/presentation"
os.makedirs(f"{base_dir}/middleware", exist_ok=True)
os.makedirs(f"{base_dir}/api/v1", exist_ok=True)
os.makedirs(f"{base_dir}/api/v1/__init__.py", exist_ok=True)

with open(f"{base_dir}/middleware/__init__.py", "w") as f: pass
with open(f"{base_dir}/__init__.py", "w") as f: pass

with open(f"{base_dir}/middleware/logging_middleware.py", "w") as f:
    f.write("from starlette.middleware.base import BaseHTTPMiddleware\nclass LoggingMiddleware(BaseHTTPMiddleware):\n    async def dispatch(self, request, call_next):\n        return await call_next(request)\n")

with open(f"{base_dir}/middleware/error_handler.py", "w") as f:
    f.write("def setup_exception_handlers(app):\n    pass\n")

routers = [
    "departments", "employees", "roles", "permissions", 
    "asset_categories", "asset_allocations", "shared_resources", 
    "resource_bookings", "maintenance_requests", "audit_cycles", 
    "notifications", "dashboard", "audit_logs"
]

for r in routers:
    with open(f"{base_dir}/api/v1/{r}.py", "w") as f:
        f.write(f"from fastapi import APIRouter\nrouter = APIRouter()\n")

assets_router_code = """from fastapi import APIRouter
from src.infrastructure.firestore.client import db

router = APIRouter()

@router.get("")
async def get_assets():
    assets_ref = db.collection('assets').stream()
    assets = []
    for doc in assets_ref:
        asset_data = doc.to_dict()
        asset_data['id'] = doc.id
        assets.append(asset_data)
    return {"data": assets}
"""
with open(f"{base_dir}/api/v1/assets.py", "w") as f:
    f.write(assets_router_code)

print("Backend presentation structure created!")
