import pytest
from fastapi import status
from app.models import Order, OrderItem, Product, Category
from decimal import Decimal

class TestOrders:
    """Test order endpoints"""
    
    def test_create_order(self, client, test_user, test_product):
        """Test creating order"""
        # Login first
        login_response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "testpassword"
        })
        token = login_response.json()["access_token"]
        
        # Create order
        response = client.post("/orders/", 
                             json={
                                 "total_amount": 199.98,
                                 "shipping_address": "123 Test St",
                                 "notes": "Test order",
                                 "items": [
                                     {
                                         "product_id": test_product.id,
                                         "quantity": 2,
                                         "unit_price": 99.99
                                     }
                                 ]
                             },
                             headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user_id"] == test_user.id
        assert data["total_amount"] == 199.98
        assert len(data["order_items"]) == 1
    
    def test_create_order_insufficient_stock(self, client, test_user, test_product):
        """Test creating order with insufficient stock"""
        # Login first
        login_response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "testpassword"
        })
        token = login_response.json()["access_token"]
        
        # Create order with more quantity than available stock
        response = client.post("/orders/", 
                             json={
                                 "total_amount": 999.99,
                                 "shipping_address": "123 Test St",
                                 "items": [
                                     {
                                         "product_id": test_product.id,
                                         "quantity": 200,  # More than available stock (100)
                                         "unit_price": 99.99
                                     }
                                 ]
                             },
                             headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Insufficient stock" in response.json()["detail"]
    
    def test_create_order_product_not_found(self, client, test_user):
        """Test creating order with non-existent product"""
        # Login first
        login_response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "testpassword"
        })
        token = login_response.json()["access_token"]
        
        # Create order with non-existent product
        response = client.post("/orders/", 
                             json={
                                 "total_amount": 99.99,
                                 "shipping_address": "123 Test St",
                                 "items": [
                                     {
                                         "product_id": 99999,  # Non-existent product
                                         "quantity": 1,
                                         "unit_price": 99.99
                                     }
                                 ]
                             },
                             headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "not found" in response.json()["detail"]
    
    def test_get_orders(self, client, test_user):
        """Test getting orders"""
        # Login first
        login_response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "testpassword"
        })
        token = login_response.json()["access_token"]
        
        # Get orders
        response = client.get("/orders/", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
    
    def test_get_orders_unauthorized(self, client):
        """Test getting orders without token"""
        response = client.get("/orders/")
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_get_order_by_id(self, client, test_user, test_product):
        """Test getting order by ID"""
        # Login first
        login_response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "testpassword"
        })
        token = login_response.json()["access_token"]
        
        # Create order first
        create_response = client.post("/orders/", 
                                    json={
                                        "total_amount": 99.99,
                                        "shipping_address": "123 Test St",
                                        "items": [
                                            {
                                                "product_id": test_product.id,
                                                "quantity": 1,
                                                "unit_price": 99.99
                                            }
                                        ]
                                    },
                                    headers={"Authorization": f"Bearer {token}"})
        order_id = create_response.json()["id"]
        
        # Get order by ID
        response = client.get(f"/orders/{order_id}", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == order_id
        assert data["user_id"] == test_user.id
    
    def test_get_order_not_found(self, client, test_user):
        """Test getting non-existent order"""
        # Login first
        login_response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "testpassword"
        })
        token = login_response.json()["access_token"]
        
        # Get non-existent order
        response = client.get("/orders/99999", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_update_order(self, client, test_user, test_product):
        """Test updating order"""
        # Login first
        login_response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "testpassword"
        })
        token = login_response.json()["access_token"]
        
        # Create order first
        create_response = client.post("/orders/", 
                                    json={
                                        "total_amount": 99.99,
                                        "shipping_address": "123 Test St",
                                        "items": [
                                            {
                                                "product_id": test_product.id,
                                                "quantity": 1,
                                                "unit_price": 99.99
                                            }
                                        ]
                                    },
                                    headers={"Authorization": f"Bearer {token}"})
        order_id = create_response.json()["id"]
        
        # Update order
        response = client.put(f"/orders/{order_id}", 
                            json={"notes": "Updated notes"},
                            headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["notes"] == "Updated notes"
    
    def test_update_order_status_admin(self, client, test_admin_user, test_user, test_product):
        """Test updating order status as admin"""
        # Login as regular user and create order
        login_response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "testpassword"
        })
        token = login_response.json()["access_token"]
        
        create_response = client.post("/orders/", 
                                    json={
                                        "total_amount": 99.99,
                                        "shipping_address": "123 Test St",
                                        "items": [
                                            {
                                                "product_id": test_product.id,
                                                "quantity": 1,
                                                "unit_price": 99.99
                                            }
                                        ]
                                    },
                                    headers={"Authorization": f"Bearer {token}"})
        order_id = create_response.json()["id"]
        
        # Login as admin and update status
        admin_login_response = client.post("/auth/login", json={
            "username": "admin",
            "password": "admin"
        })
        admin_token = admin_login_response.json()["access_token"]
        
        response = client.put(f"/orders/{order_id}", 
                            json={"status": "shipped"},
                            headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "shipped"
    
    def test_update_order_status_non_admin(self, client, test_user, test_product):
        """Test updating order status as non-admin"""
        # Login first
        login_response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "testpassword"
        })
        token = login_response.json()["access_token"]
        
        # Create order first
        create_response = client.post("/orders/", 
                                    json={
                                        "total_amount": 99.99,
                                        "shipping_address": "123 Test St",
                                        "items": [
                                            {
                                                "product_id": test_product.id,
                                                "quantity": 1,
                                                "unit_price": 99.99
                                            }
                                        ]
                                    },
                                    headers={"Authorization": f"Bearer {token}"})
        order_id = create_response.json()["id"]
        
        # Try to update status (should not work for non-admin)
        response = client.put(f"/orders/{order_id}", 
                            json={"status": "shipped"},
                            headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == status.HTTP_200_OK
        # Status should not change for non-admin
        data = response.json()
        assert data["status"] == "pending"  # Original status
