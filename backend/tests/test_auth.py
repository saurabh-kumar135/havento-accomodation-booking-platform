import pytest
import uuid

@pytest.mark.asyncio
async def test_auth_flow(client):
    unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    
    # 1. Signup
    signup_payload = {
        "firstName": "Test",
        "lastName": "User",
        "email": unique_email,
        "password": "Password123!",
        "userType": "guest"
    }
    signup_res = await client.post("/api/signup", json=signup_payload)
    assert signup_res.status_code == 200 or signup_res.status_code == 201
    assert signup_res.json()["success"] is True

    # 2. Login
    login_payload = {
        "email": unique_email,
        "password": "Password123!"
    }
    login_res = await client.post("/api/login", json=login_payload)
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert login_data["success"] is True
    assert "token" in login_data
    token = login_data["token"]

    # 3. Check Session with Bearer Token
    session_res = await client.get("/api/check-session", headers={"Authorization": f"Bearer {token}"})
    assert session_res.status_code == 200
    session_data = session_res.json()
    assert session_data["isLoggedIn"] is True
    assert session_data["user"]["email"] == unique_email
