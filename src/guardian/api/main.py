import os
import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import pandas as pd
from fastapi import FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.guardian.api.schemas import (
    MessageAnalysisRequest, MessageAnalysisResponse,
    TransactionScoreRequest, TransactionScoreResponse, DecisionDetail,
    TrustedContactActionRequest, TrustedContactActionResponse,
    AlertItem, AlertResolveRequest, AlertResolveResponse
)
from src.guardian.engine.ladder import DecisionEngine
from src.guardian.models.text_clf import ScamTextClassifier
from src.guardian.models.txn_model import TransactionRiskModel
from src.guardian.models.anomaly import BehavioralAnomalyDetector
from src.guardian.models.explain import ModelExplainer
from src.guardian.features.graph import build_transaction_graph, export_subgraph_json

app = FastAPI(
    title="Guardian MFS Scam Shield API",
    version="1.0.0",
    description="Multi-modal AI scam intelligence and dynamic friction ladder for upay"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Persistent In-Memory State for Alerts & Decisions
ALERTS_STORE: Dict[str, Dict[str, Any]] = {}
DECISIONS_STORE: Dict[str, Dict[str, Any]] = {}

# Lazy-loaded component state
COMPONENTS: Dict[str, Any] = {}

def get_components():
    if not COMPONENTS:
        artifacts_dir = "models_artifacts"
        data_dir = "data"
        COMPONENTS["engine"] = DecisionEngine()
        
        # Load models if artifacts exist, else provide fallback stubs
        text_path = os.path.join(artifacts_dir, "text_clf.joblib")
        txn_path = os.path.join(artifacts_dir, "txn_model.joblib")
        anom_path = os.path.join(artifacts_dir, "anomaly_model.joblib")
        exp_path = os.path.join(artifacts_dir, "explainer.joblib")
        
        COMPONENTS["text_clf"] = ScamTextClassifier.load(text_path) if os.path.exists(text_path) else None
        COMPONENTS["txn_model"] = TransactionRiskModel.load(txn_path) if os.path.exists(txn_path) else None
        COMPONENTS["anomaly_model"] = BehavioralAnomalyDetector.load(anom_path) if os.path.exists(anom_path) else None
        COMPONENTS["explainer"] = ModelExplainer.load(exp_path) if os.path.exists(exp_path) else None

        # Build in-memory graph if transaction data exists
        txns_path = os.path.join(data_dir, "sample", "transactions_sample.csv")
        agents_path = os.path.join(data_dir, "sample", "agents_sample.csv")
        if os.path.exists(txns_path) and os.path.exists(agents_path):
            txns_df = pd.read_csv(txns_path)
            agents_df = pd.read_csv(agents_path)
            G, graph_risk = build_transaction_graph(txns_df, agents_df)
            COMPONENTS["graph"] = G
            COMPONENTS["graph_risk"] = graph_risk
        else:
            COMPONENTS["graph"] = None
            COMPONENTS["graph_risk"] = {}
    return COMPONENTS

# Role-Based Access Helper
def require_analyst_role(x_role: Optional[str] = Header(None)):
    if x_role != "analyst":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted. Header 'X-Role: analyst' required for operational security."
        )

@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": "guardian-shield",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "offline-safe"
    }

@app.get("/v1/config", tags=["System"])
def get_masked_config():
    components = get_components()
    cfg = components["engine"].config.copy()
    return cfg

@app.post("/v1/analyze/message", response_model=MessageAnalysisResponse, tags=["Scam NLP"])
def analyze_message(payload: MessageAnalysisRequest):
    components = get_components()
    text = payload.message_text.strip()
    
    if components["text_clf"]:
        result = components["text_clf"].predict_risk(text)
    else:
        # Fallback offline keyword heuristic
        is_scam = any(w in text.lower() for w in ["otp", "pin", "ভুল করে", "লটারি", "বন্ধ"])
        result = {
            "scam_type": "otp_pin_request" if is_scam else "benign",
            "scam_probability": 0.85 if is_scam else 0.05,
            "evidence_phrases": ["detected_keyword"] if is_scam else [],
            "is_scam": is_scam
        }
        
    cfg = components["engine"].config
    bn_msg = "সতর্কতা: এই মেসেজে প্রতারণামূলক সংকেত পাওয়া গেছে।" if result["is_scam"] else "মেসেজটি স্বাভাবিক মনে হচ্ছে।"
    en_msg = "Warning: Phishing/scam pattern detected in this message." if result["is_scam"] else "Message appears normal."
    
    return MessageAnalysisResponse(
        scam_type=result["scam_type"],
        scam_probability=result["scam_probability"],
        is_scam=result["is_scam"],
        evidence_phrases=result["evidence_phrases"],
        customer_message_bn=bn_msg,
        customer_message_en=en_msg
    )

@app.post("/v1/score/transaction", response_model=TransactionScoreResponse, tags=["Decision Engine"])
def score_transaction(payload: TransactionScoreRequest):
    components = get_components()
    decision_id = f"DEC_{uuid.uuid4().hex[:10].upper()}"
    ts_now = datetime.now(timezone.utc).isoformat()
    
    # 1. NLP score if context provided
    text_scam_score = 0.0
    text_class = "benign"
    if payload.message_context:
        msg_res = analyze_message(MessageAnalysisRequest(message_text=payload.message_context))
        text_scam_score = msg_res.scam_probability
        text_class = msg_res.scam_type
        
    # 2. Graph topology risk lookup
    graph_risk_map = components.get("graph_risk", {})
    graph_risk = graph_risk_map.get(payload.recipient_id, 0.05)
    
    # 3. Tabular ML score & SHAP explanation
    amt_ratio = round(payload.amount / max(payload.typical_amount, 1.0), 2)
    feature_row = pd.DataFrame([{
        "amount_ratio_to_baseline": amt_ratio,
        "is_new_device": 1 if payload.is_new_device else 0,
        "is_new_recipient": 1 if payload.is_new_recipient else 0,
        "is_odd_hour": 0,
        "velocity_count_1h": 0,
        "velocity_count_24h": 1,
        "velocity_amount_24h": payload.amount,
        "recipient_graph_risk": graph_risk,
        "vulnerability_score": payload.vulnerability_score,
        "tenure_days": 120,
        "sent_by_mistake_risk_flag": 1 if (text_class == "sent_by_mistake" and payload.amount >= 3000) else 0
    }])
    
    txn_ml_score = 0.15
    shap_reasons = []
    anomaly_score = 0.10
    
    if components["txn_model"]:
        txn_ml_score = float(components["txn_model"].predict_risk(feature_row)[0])
    if components["anomaly_model"]:
        anomaly_score = float(components["anomaly_model"].score(feature_row)[0])
    if components["explainer"]:
        shap_reasons = components["explainer"].explain_instance(feature_row, top_k=3)
        
    # 4. Context assembly for decision ladder
    ctx = {
        "user_id": payload.user_id,
        "recipient_id": payload.recipient_id,
        "amount": payload.amount,
        "typical_amount": payload.typical_amount,
        "vulnerability_score": payload.vulnerability_score,
        "has_trusted_contact": payload.has_trusted_contact,
        "text_scam_type": text_class,
        "is_new_recipient": payload.is_new_recipient,
        "is_new_device": payload.is_new_device,
        "recipient_graph_risk": graph_risk,
        "amount_ratio_to_baseline": amt_ratio
    }
    
    decision = components["engine"].decide(
        transaction_context=ctx,
        raw_message_text=payload.message_context or "",
        txn_ml_score=txn_ml_score,
        text_scam_score=text_scam_score,
        graph_risk=graph_risk,
        anomaly_score=anomaly_score,
        shap_reasons=shap_reasons
    )
    
    # Store decision
    DECISIONS_STORE[decision_id] = {
        "decision_id": decision_id,
        "timestamp": ts_now,
        "request": payload.model_dump(),
        "decision": decision
    }
    
    # If routed to L4 (Analyst queue), generate an alert record
    if decision["action_level"] == "L4":
        alert_id = f"ALT_{uuid.uuid4().hex[:8].upper()}"
        ALERTS_STORE[alert_id] = {
            "alert_id": alert_id,
            "timestamp": ts_now,
            "decision_id": decision_id,
            "user_id": payload.user_id,
            "recipient_id": payload.recipient_id,
            "amount": payload.amount,
            "action_level": decision["action_level"],
            "risk_score": decision["risk_score"],
            "status": "pending_review",
            "analyst_narrative": decision["analyst_narrative"]
        }
        
    return TransactionScoreResponse(
        decision_id=decision_id,
        timestamp=ts_now,
        decision=DecisionDetail(**decision)
    )

@app.post("/v1/decision/{decision_id}/trusted-contact", response_model=TrustedContactActionResponse, tags=["Customer Experience"])
def trusted_contact_action(decision_id: str, payload: TrustedContactActionRequest):
    if decision_id not in DECISIONS_STORE:
        raise HTTPException(status_code=404, detail="Decision ID not found.")
        
    status_str = "APPROVED_BY_TRUSTED_CONTACT" if payload.action == "approve" else "DENIED_BY_TRUSTED_CONTACT"
    DECISIONS_STORE[decision_id]["trusted_contact_resolution"] = {
        "status": status_str,
        "contact_id": payload.trusted_contact_id,
        "notes": payload.notes,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    msg = "ট্রান্সফার অনুমোদিত হয়েছে।" if payload.action == "approve" else "অভিভাবক লেনদেনটি বাতিল করেছেন।"
    return TrustedContactActionResponse(
        decision_id=decision_id,
        status=status_str,
        message=msg
    )

@app.get("/v1/alerts", response_model=List[AlertItem], tags=["Analyst Operations"])
def get_alert_queue(status_filter: Optional[str] = Query(None), x_role: Optional[str] = Header(None)):
    require_analyst_role(x_role)
    alerts = list(ALERTS_STORE.values())
    if status_filter:
        alerts = [a for a in alerts if a["status"] == status_filter]
    return sorted(alerts, key=lambda x: x["timestamp"], reverse=True)

@app.post("/v1/alerts/{alert_id}/resolve", response_model=AlertResolveResponse, tags=["Analyst Operations"])
def resolve_alert(alert_id: str, payload: AlertResolveRequest, x_role: Optional[str] = Header(None)):
    require_analyst_role(x_role)
    if alert_id not in ALERTS_STORE:
        raise HTTPException(status_code=404, detail="Alert ID not found.")
        
    ALERTS_STORE[alert_id]["status"] = payload.resolution
    ALERTS_STORE[alert_id]["resolution_notes"] = payload.resolution_notes
    ALERTS_STORE[alert_id]["resolved_by"] = payload.analyst_id
    ALERTS_STORE[alert_id]["resolved_at"] = datetime.now(timezone.utc).isoformat()
    
    return AlertResolveResponse(
        alert_id=alert_id,
        status=payload.resolution,
        updated_at=ALERTS_STORE[alert_id]["resolved_at"]
    )

@app.get("/v1/metrics/impact", tags=["Impact & Economics"])
def get_impact_metrics():
    eval_path = "data/eval_results.json"
    if os.path.exists(eval_path):
        with open(eval_path, "r", encoding="utf-8") as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="Evaluation results not yet generated. Run scripts/evaluate.sh first.")

@app.get("/v1/graph/{wallet_id}", tags=["Graph Intelligence"])
def get_wallet_subgraph(wallet_id: str):
    components = get_components()
    G = components.get("graph")
    risk_map = components.get("graph_risk", {})
    if G is not None:
        subgraph_json = export_subgraph_json(G, risk_map, center_node=wallet_id, max_nodes=25)
        return json.loads(subgraph_json)
    return {"nodes": [{"id": wallet_id, "label": wallet_id, "risk": 0.05}], "edges": []}

# Serve web static UI if directory exists
if os.path.exists("src/guardian/web"):
    app.mount("/", StaticFiles(directory="src/guardian/web", html=True), name="web")