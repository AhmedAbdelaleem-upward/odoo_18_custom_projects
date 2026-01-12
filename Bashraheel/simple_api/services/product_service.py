import logging
from typing import Dict, Any
from odoo import models

from ..utils.responses import success_list_response, success_response

_logger = logging.getLogger(__name__)


class ProductService(models.AbstractModel):
    _name = 'simple.product.service'
    _description = 'Product Service for Simple API'

    def get_products(
        self,
        partner_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Retrieve list of products from product.template"""
        Product = self.env['product.template']
        domain = []  # No filter, return all products

        total_count = Product.search_count(domain)
        products = Product.search(domain, limit=limit, offset=offset, order='id desc')

        data = []
        for rec in products:
            data.append({
                "id": rec.id,
                "name": rec.name,
            })

        return success_list_response(data, total_count)

    def create_product(
        self,
        partner_id: int,
        data: dict
    ) -> Dict[str, Any]:
        """Create new product in product.template"""
        Product = self.env['product.template']

        # Only set name, let Odoo handle defaults for other fields
        product_vals = {
            'name': data.get('name'),
        }

        new_product = Product.create(product_vals)

        result_data = {
            "id": new_product.id,
            "name": new_product.name,
        }

        return success_response(result_data)
