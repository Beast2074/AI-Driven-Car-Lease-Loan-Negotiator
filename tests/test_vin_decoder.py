from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.main import app

client = TestClient(app)

def test_vin_decoder_valid():
    """Test valid VIN decoding via NHTSA API"""
    vin = "1HGCG5655WA036874" # 1998 Honda Accord
    response = client.get(f"/vin/{vin}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    veh = data.get("vehicle_info", {})
    assert veh.get("make", "").upper() == "HONDA"

def test_vin_decoder_invalid():
    """Test invalid VIN length rejection"""
    response = client.get("/vin/INVALID123")
    assert response.status_code == 400
