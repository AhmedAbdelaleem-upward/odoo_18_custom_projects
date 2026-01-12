import logging
from fastapi import APIRouter, status, Depends, Query

from ..schemas.product_schemas import (
    ProductListResponse,
    ProductResponse,
    ProductCreateRequest,
)
from ..core.constants import SERVICE_PRODUCT
from ..auth.dependencies import create_jwt_auth_dependency
from ..utils.context_manager import user_env
from ..utils.decorators import handle_router_errors

_logger = logging.getLogger(__name__)


def create_product_router(registry, uid, context):
    """Create and return the product API router"""
    router = APIRouter(
        prefix="/product",
        tags=["Products"],
    )

    # Create JWT auth dependency with captured context
    jwt_auth = create_jwt_auth_dependency(registry, uid, context)

    @router.get(
        "/",
        response_model=ProductListResponse,
        status_code=status.HTTP_200_OK,
        summary="List Products",
        description="Retrieve list of products from product.template",
    )
    @handle_router_errors
    def get_products(
        auth: dict = Depends(jwt_auth),
        limit: int = Query(50, ge=1, le=100),
        offset: int = Query(0, ge=0),
    ):
        """Get list of products with pagination"""
        with user_env(registry, context, auth) as (env, partner_id, cr):
            service = env[SERVICE_PRODUCT]
            return service.get_products(partner_id, limit=limit, offset=offset)

    @router.post(
        "/",
        response_model=ProductResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Create Product",
        description="Create new product in product.template (name only)",
    )
    @handle_router_errors
    def create_product(
        request: ProductCreateRequest,
        auth: dict = Depends(jwt_auth),
    ):
        """Create new product with name only"""
        with user_env(registry, context, auth) as (env, partner_id, cr):
            service = env[SERVICE_PRODUCT]
            result = service.create_product(partner_id, request.dict())
            cr.commit()  # CRITICAL: commit after mutations
            return result

    return router
