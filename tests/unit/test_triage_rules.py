import pytest
from src.domain.rules.triage_rules import PostOpTriageRules

def test_total_hip_pod1_normal():
    # Sarah Johnson's POD 1 response from deep dive: pain 5, no red flags
    symptoms = {
        "pain_score": 5,
        "fever_or_drainage": False,
        "calf_swelling": False,
        "shortness_of_breath": False,
        "nausea_or_vomiting": False
    }
    eval_res = PostOpTriageRules.evaluate_recovery_trajectory("27130", pod_day=1, symptoms=symptoms)
    assert eval_res.risk_level == "LOW_RISK"
    assert eval_res.nurse_escalation_required is False
    assert "on track" in eval_res.recommended_patient_message.lower()

def test_total_hip_pod1_calf_swelling_dvt_alert():
    # Critical red flag: calf swelling on POD 1
    symptoms = {
        "pain_score": 5,
        "fever_or_drainage": False,
        "calf_swelling": True,
        "shortness_of_breath": False,
        "nausea_or_vomiting": False
    }
    eval_res = PostOpTriageRules.evaluate_recovery_trajectory("27130", pod_day=1, symptoms=symptoms)
    assert eval_res.risk_level == "HIGH_RISK"
    assert eval_res.nurse_escalation_required is True
    assert "deep vein thrombosis" in eval_res.clinical_rationale.lower()

def test_total_hip_pod7_milestone():
    # Day 7 check-in: pain 2
    symptoms = {
        "pain_score": 2,
        "fever_or_drainage": False,
        "calf_swelling": False,
        "shortness_of_breath": False,
        "nausea_or_vomiting": False
    }
    eval_res = PostOpTriageRules.evaluate_recovery_trajectory("27130", pod_day=7, symptoms=symptoms)
    assert eval_res.risk_level == "LOW_RISK"
    assert eval_res.nurse_escalation_required is False
