"""Product catalog service implementing business logic for products."""

import math
from app.repositories.product_repository import ProductRepository


class ProductService:
    """Business operations for product management and catalog browsing."""

    def __init__(self, product_repo=None):
        self.repo = product_repo or ProductRepository()

    def create_product(self, product_data):
        """Create a new product in catalog."""
        return self.repo.create(product_data)

    def get_product(self, product_id):
        """Get product by ID."""
        return self.repo.get_by_id(product_id)

    def list_products(self, sort=None, category=None, page=1, limit=10):
        """
        List products with category filtering, numerical price sorting, and pagination.
        """
        filter_query = {}
        if category:
            filter_query["category"] = category

        sort_field = None
        sort_order = 1
        if sort == "price_asc":
            sort_field = "price"
            sort_order = 1
        elif sort == "price_desc":
            sort_field = "price"
            sort_order = -1

        skip = (page - 1) * limit
        products, total = self.repo.list_products(
            filter_query=filter_query,
            sort_field=sort_field,
            sort_order=sort_order,
            skip=skip,
            limit=limit,
        )

        total_pages = math.ceil(total / limit) if total > 0 else 0

        return {
            "products": products,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": total_pages,
            },
        }

    def update_product(self, product_id, update_data):
        """Update product information."""
        return self.repo.update(product_id, update_data)

    def delete_product(self, product_id):
        """Delete product by ID."""
        return self.repo.delete(product_id)

