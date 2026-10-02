from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class MessageAnalysisRequest(BaseModel):
    message_text: str = Field(..., min_length=1, max_length=1000, description="Raw SMS or chat message content")

class MessageAnalysisResponse(BaseModel):
    scam_type: str
    scam_probability: float
    is_scam: bool
    evidence_phrases: List[str]
    customer_message_bn: str
    customer_message_en: str

class TransactionScoreRequest(BaseModel):
    user_id: str = Field(..., examples=["U_100042"])
    recipient_id: str = Field(..., examples=["01711002233"])
    amount: float = Field(..., gt=0.0, examples=[7500.0])
    txn_type: str = Field(default="send_money", examples=["send_money"])
    device_id: Optional[str] = Field(default=None, examples=["DEV_8291_42"])
    message_context: Optional[str] = Field(default=None, description="Optional suspicious message that prompted transfer")
    is_new_recipient: Optional[bool] = Field(default=True)
    is_new_device: Optional[bool] = Field(default=False)
    vulnerability_score: Optional[float] = Field(default=0.35, ge=0.0, le=1.0)
    typical_amount: Optional[float] = Field(default=1500.0, gt=0.0)
    has_trusted_contact: Optional[bool] = Field(default=True)

class DecisionDetail(BaseModel):
    action_level: str
    risk_score: float
    is_vulnerable_user: bool
    reason_codes: List[str]
    rule_trace: List[str]
    customer_message_bn: str
    customer_message_en: str
    analyst_narrative: str
    evidence: Dict[str, Any]

class TransactionScoreResponse(BaseModel):
    decision_id: str
    timestamp: str
    decision: DecisionDetail

class TrustedContactActionRequest(BaseModel):
    action: str = Field(..., pattern="^(approve|deny)$", examples=["approve"])
    trusted_contact_id: str = Field(..., examples=["CONTACT_01700000000"])
    notes: Optional[str] = None

class TrustedContactActionResponse(BaseModel):
    decision_id: str
    status: str
    message: str

class AlertItem(BaseModel):
    alert_id: str
    timestamp: str
    decision_id: str
    user_id: str
    recipient_id: str
    amount: float
    action_level: str
    risk_score: float
    status: str # "pending_review", "confirmed_scam", "false_positive"
    analyst_narrative: str

class AlertResolveRequest(BaseModel):
    resolution: str = Field(..., pattern="^(confirmed_scam|false_positive|escalated)$")
    analyst_id: str
    resolution_notes: Optional[str] = None

class AlertResolveResponse(BaseModel):
    alert_id: str
    status: str
    updated_at: str