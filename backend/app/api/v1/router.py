from fastapi import APIRouter
from .endpoints import projects, credentials, proxies, tasks, backups, system

api_router = APIRouter()
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(credentials.router, prefix="/credentials", tags=["Credentials"])
api_router.include_router(proxies.router, prefix="/proxies", tags=["Proxies"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
api_router.include_router(backups.router, prefix="/backups", tags=["Backups"])
api_router.include_router(system.router, prefix="/system", tags=["System"])