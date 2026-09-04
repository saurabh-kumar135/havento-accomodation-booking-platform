import pytest

@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "FastAPI" in data["service"]

@pytest.mark.asyncio
async def test_get_homes(client):
    response = await client.get("/api/homes")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "registeredHomes" in data
    assert isinstance(data["registeredHomes"], list)

@pytest.mark.asyncio
async def test_agent_suggestions(client):
    response = await client.get("/api/agent/suggestions")
    assert response.status_code == 200
    data = response.json()
    assert "suggestions" in data
    assert len(data["suggestions"]) > 0
