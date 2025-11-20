from fastapi.testclient import TestClient
from app.main import app  # Adjust to your main FastAPI app import

client = TestClient(app)

def test_basic_request():
    response = client.post("/triage", json={"description": "My printer is not working"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)  
    assert "result" in data or "category" in data  

def test_empty_description():
    response = client.post("/triage", json={"description": ""})
    assert response.status_code in {200, 400}  

def test_long_description():
    long_ticket = "Very long " + ("description " * 1000)
    response = client.post("/triage", json={"description": long_ticket})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)

def test_missing_field():
    response = client.post("/triage", json={})
    assert response.status_code in {422, 400}  # Should be error for missing payload
