import pytest
from fastapi import status

from app.models import Category, Product


class TestProducts:
    """Test product endpoints"""

    async def test_get_categories(self, client):
        """Test getting categories"""
        response = await client.get("/products/categories")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    async def test_create_category_admin(self, client, test_admin_user):
        """Test creating category as admin"""
        # Login as admin
        login_response = await client.post(
            "/auth/login", json={"username": "admin", "password": "admin"}
        )
        token = login_response.json()["access_token"]

        # Create category
        response = await client.post(
            "/products/categories",
            json={"name": "New Category", "description": "New category description"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "New Category"

    async def test_create_category_non_admin(self, client, test_user):
        """Test creating category as non-admin"""
        # Login as regular user
        login_response = await client.post(
            "/auth/login", json={"username": "testuser", "password": "testpassword"}
        )
        token = login_response.json()["access_token"]

        # Try to create category
        response = await client.post(
            "/products/categories",
            json={"name": "New Category", "description": "New category description"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_get_products(self, client):
        """Test getting products"""
        response = await client.get("/products/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data

    async def test_get_products_with_filters(self, client, test_product):
        """Test getting products with filters"""
        response = await client.get("/products/?category_id=1&min_price=50&max_price=200")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data

    async def test_get_product_by_id(self, client, test_product):
        """Test getting product by ID"""
        response = await client.get(f"/products/{test_product.id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_product.id
        assert data["name"] == "Test Product"

    async def test_get_product_not_found(self, client):
        """Test getting non-existent product"""
        response = await client.get("/products/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_create_product_admin(self, client, test_admin_user, test_category):
        """Test creating product as admin"""
        # Login as admin
        login_response = await client.post(
            "/auth/login", json={"username": "admin", "password": "admin"}
        )
        token = login_response.json()["access_token"]

        # Create product
        response = await client.post(
            "/products/",
            json={
                "name": "New Product",
                "description": "New product description",
                "price": 199.99,
                "stock_quantity": 50,
                "category_id": test_category.id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "New Product"
        assert data["price"] == 199.99

    async def test_create_product_non_admin(self, client, test_user, test_category):
        """Test creating product as non-admin"""
        # Login as regular user
        login_response = await client.post(
            "/auth/login", json={"username": "testuser", "password": "testpassword"}
        )
        token = login_response.json()["access_token"]

        # Try to create product
        response = await client.post(
            "/products/",
            json={
                "name": "New Product",
                "description": "New product description",
                "price": 199.99,
                "stock_quantity": 50,
                "category_id": test_category.id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_update_product_admin(self, client, test_admin_user, test_product):
        """Test updating product as admin"""
        # Login as admin
        login_response = await client.post(
            "/auth/login", json={"username": "admin", "password": "admin"}
        )
        token = login_response.json()["access_token"]

        # Update product
        response = await client.put(
            f"/products/{test_product.id}",
            json={"name": "Updated Product", "price": 149.99},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Product"
        assert data["price"] == 149.99

    async def test_update_product_non_admin(self, client, test_user, test_product):
        """Test updating product as non-admin"""
        # Login as regular user
        login_response = await client.post(
            "/auth/login", json={"username": "testuser", "password": "testpassword"}
        )
        token = login_response.json()["access_token"]

        # Try to update product
        response = await client.put(
            f"/products/{test_product.id}",
            json={"name": "Updated Product"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
