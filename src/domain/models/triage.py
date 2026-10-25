from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class SymptomReport(BaseModel):
    pod_day: int
    reported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    pain_score: int # 1 to 10
    fever_or_drainage: bool
    calf_swelling: bool
    shortness_of_breath: bool
    nausea_or_vomiting: bool
    raw_response: str

class TriageEvaluation(BaseModel):
    pod_day: int
    risk_level: str # "LOW_RISK", "MODERATE_RISK", "HIGH_RISK"
    nurse_escalation_required: bool
    clinical_rationale: str
    recommended_patient_message: str
