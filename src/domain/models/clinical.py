from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class RiskTier(str, Enum):
    TIER_1_AUTO = "TIER_1_AUTO"
    TIER_2_REVIEWED = "TIER_2_REVIEWED"
    TIER_3_ESCALATED = "TIER_3_ESCALATED"

class ClinicalFlag(BaseModel):
    code: str
    name: str
    severity: str # "LOW", "MODERATE", "HIGH", "CRITICAL"
    action_required: str

class ClinicalRiskProfile(BaseModel):
    patient_id: str
    encounter_id: str
    asa_class: int # 1 to 6
    rcri_score: int # 0 to 6
    composite_score: float
    assigned_tier: RiskTier
    flags: List[ClinicalFlag] = Field(default_factory=list)
    summary: str
    requires_human_signoff: bool
