import pytest
from fastapi import status
from app.models import User

class TestUsers:
    """Test user endpoints"""
    
    def test_get_current_user(self, client, test_user):
        """Test getting current user info"""
        # Login first
        login_response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "testpassword"
        })
        token = login_response.json()["access_token"]
        
        # Get current user
        response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
    
    def test_get_current_user_unauthorized(self, client):
        """Test getting current user without token"""
        response = client.get("/users/me")
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_get_users_admin(self, client, test_admin_user):
        """Test getting users list as admin"""
        # Login as admin
        login_response = client.post("/auth/login", json={
            "username": "admin",
            "password": "admin"
        })
        token = login_response.json()["access_token"]
        
        # Get users list
        response = client.get("/users/", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
    
    def test_get_users_non_admin(self, client, test_user):
        """Test getting users list as non-admin"""
        # Login as regular user
        login_response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "testpassword"
        })
        token = login_response.json()["access_token"]
        
        # Try to get users list
        response = client.get("/users/", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_get_user_by_id(self, client, test_user):
        """Test getting user by ID"""
        # Login first
        login_response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "testpassword"
        })
        token = login_response.json()["access_token"]
        
        # Get user by ID
        response = client.get(f"/users/{test_user.id}", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_user.id
        assert data["username"] == "testuser"
    
    def test_get_user_by_id_unauthorized(self, client, test_user):
        """Test getting user by ID without token"""
        response = client.get(f"/users/{test_user.id}")
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_update_user(self, client, test_user):
        """Test updating user"""
        # Login first
        login_response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "testpassword"
        })
        token = login_response.json()["access_token"]
        
        # Update user
        response = client.put(f"/users/{test_user.id}", 
                            json={"full_name": "Updated Name"},
                            headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["full_name"] == "Updated Name"
    
    def test_update_user_unauthorized(self, client, test_user):
        """Test updating user without token"""
        response = client.put(f"/users/{test_user.id}", 
                            json={"full_name": "Updated Name"})
        assert response.status_code == status.HTTP_403_FORBIDDEN
