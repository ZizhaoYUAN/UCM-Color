from fastapi import APIRouter

from app.api.routes import catalog, health, inventory, member, order, promotion, store

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(store.router)
api_router.include_router(catalog.router)
api_router.include_router(inventory.router)
api_router.include_router(member.router)
api_router.include_router(order.router)
api_router.include_router(promotion.router)
