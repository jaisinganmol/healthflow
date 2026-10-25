import pytest
from src.domain.rules.coding_rules import BillingDiscrepancyEngine

def test_down_coding_detection_ckd():
    # Patient chart has CKD 3a documented, but biller omitted N18.30
    res = BillingDiscrepancyEngine.audit_claim(
        cpt_codes=["27130"],
        icd10_codes=["M17.11"], # Only osteoarthritis billed
        charted_conditions=["Osteoarthritis right hip", "CKD stage 3a (moderate renal failure)"],
        operative_notes="Completed total hip replacement without incident."
    )
    assert res["clean_claim"] is False
    assert res["discrepancies_found"] is True
    down_codes = [d for d in res["discrepancies"] if d["type"] == "DOWN_CODING"]
    assert len(down_codes) >= 1
    assert any(d["code"] == "N18.30" for d in down_codes)
    # Check allowable was adjusted up for CC tier
    assert res["allowable_reimbursement"] > BillingDiscrepancyEngine.BASE_ALLOWABLE

def test_up_coding_detection_unsupported_heart_failure():
    # Claim includes Heart Failure (I50.9) but operative notes and chart have zero mentions
    res = BillingDiscrepancyEngine.audit_claim(
        cpt_codes=["27130"],
        icd10_codes=["M17.11", "I50.9"], # Fraudulent or mistaken I50 code
        charted_conditions=["Osteoarthritis right hip"],
        operative_notes="Completed total hip replacement. Patient healthy throughout."
    )
    assert res["clean_claim"] is False
    up_codes = [d for d in res["discrepancies"] if d["type"] == "UP_CODING"]
    assert len(up_codes) >= 1
    assert any(d["code"] == "I50.9" for d in up_codes)
    assert any(d["severity"] == "CRITICAL" for d in up_codes)

def test_clean_claim():
    # Both diagnoses properly substantiated
    res = BillingDiscrepancyEngine.audit_claim(
        cpt_codes=["27130"],
        icd10_codes=["M17.11", "N18.30"],
        charted_conditions=["Osteoarthritis right hip", "CKD stage 3a"],
        operative_notes="Total hip arthroplasty performed successfully."
    )
    assert res["clean_claim"] is True
    assert len(res["discrepancies"]) == 0
