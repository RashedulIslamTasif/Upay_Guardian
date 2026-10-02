import pytest
from fastapi.testclient import TestClient
from src.guardian.api.main import app

client = TestClient(app)

def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["service"] == "guardian-shield"

def test_analyze_message_scam():
    payload = {"message_text": "জরুরি: আপনার অ্যাকাউন্ট বন্ধ হবে অবিলম্বে পিন ও ওটিপি দিন"}
    res = client.post("/v1/analyze/message", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "scam_probability" in data
    assert "customer_message_bn" in data

def test_score_transaction_benign():
    payload = {
        "user_id": "U_1001",
        "recipient_id": "U_2002",
        "amount": 500.0,
        "typical_amount": 600.0,
        "is_new_recipient": False,
        "is_new_device": False,
        "vulnerability_score": 0.20
    }
    res = client.post("/v1/score/transaction", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "decision_id" in data
    assert data["decision"]["action_level"] == "L0"

def test_analyst_role_security_enforcement():
    # Attempting to fetch alerts without analyst role header must yield 403 Forbidden
    res = client.get("/v1/alerts")
    assert res.status_code == 403
    
    # Supplying header allows legitimate analyst access
    res_auth = client.get("/v1/alerts", headers={"X-Role": "analyst"})
    assert res_auth.status_code == 200

def test_trusted_contact_flow():
    # Score a suspicious transaction that triggers friction
    score_payload = {
        "user_id": "U_1002",
        "recipient_id": "01999887766",
        "amount": 9500.0,
        "typical_amount": 1000.0,
        "message_context": "আপনার লটারি প্রাইজ পেতে ফি পাঠান",
        "is_new_recipient": True,
        "vulnerability_score": 0.75
    }
    score_res = client.post("/v1/score/transaction", json=score_payload)
    dec_id = score_res.json()["decision_id"]
    
    # Co-approve by trusted contact
    approve_res = client.post(
        f"/v1/decision/{dec_id}/trusted-contact",
        json={"action": "approve", "trusted_contact_id": "CONTACT_01711223344"}
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "APPROVED_BY_TRUSTED_CONTACT"