import pytest
from fastapi import status
from app.models import User

class TestAuth:
    """Test authentication endpoints"""
    
    def test_seed_admin_user(self, client):
        """Test seeding admin user"""
        response = client.post("/auth/seed")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Admin user created"
        assert data["username"] == "admin"
    
    def test_seed_admin_user_already_exists(self, client, test_admin_user):
        """Test seeding admin user when already exists"""
        response = client.post("/auth/seed")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Admin user already exists"
    
    def test_login_success(self, client, test_user):
        """Test successful login"""
        response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "testpassword"
        })
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        response = client.post("/auth/login", json={
            "username": "nonexistent",
            "password": "wrongpassword"
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_register_success(self, client):
        """Test successful user registration"""
        response = client.post("/auth/register", json={
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "newpassword",
            "full_name": "New User"
        })
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert "id" in data
    
    def test_register_duplicate_email(self, client, test_user):
        """Test registration with duplicate email"""
        response = client.post("/auth/register", json={
            "email": "test@example.com",
            "username": "differentuser",
            "password": "password",
            "full_name": "Different User"
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Email already registered" in response.json()["detail"]
    
    def test_register_duplicate_username(self, client, test_user):
        """Test registration with duplicate username"""
        response = client.post("/auth/register", json={
            "email": "different@example.com",
            "username": "testuser",
            "password": "password",
            "full_name": "Different User"
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Username already taken" in response.json()["detail"]
