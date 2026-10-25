from typing import List, Dict, Any

class BillingDiscrepancyEngine:
    """
    Dual-direction discrepancy auditor for hospital billing and coding.
    - Prevents down-coding (omitted documented comorbidities resulting in lost hospital reimbursement).
    - Prevents up-coding (submitting higher-intensity codes unsupported by clinical notes, creating audit/fraud liability).
    """

    # Standard reimbursement baseline for major arthroplasty (MS-DRG 470 / 469)
    BASE_ALLOWABLE = 14200.00
    CC_MCC_ADJUSTMENT = 3800.00  # Additional reimbursement when Complication/Comorbidity (CC) is documented

    @classmethod
    def audit_claim(
        cls,
        cpt_codes: List[str],
        icd10_codes: List[str],
        charted_conditions: List[str],
        operative_notes: str
    ) -> Dict[str, Any]:
        discrepancies: List[Dict[str, Any]] = []
        allowable = cls.BASE_ALLOWABLE

        charted_lower = [c.lower() for c in charted_conditions]
        icd_set = set(icd10_codes)

        # 1. Down-Coding Audit: Chronic Kidney Disease Stage 3 (N18.30)
        # If CKD 3 was documented in chart/labs but omitted from billing diagnosis codes
        has_charted_ckd = any("ckd" in c or "chronic kidney" in c or "n18" in c for c in charted_lower)
        has_billed_ckd = any(code.startswith("N18.3") for code in icd_set)
        if has_charted_ckd and not has_billed_ckd:
            discrepancies.append({
                "type": "DOWN_CODING",
                "code": "N18.30",
                "severity": "MODERATE",
                "description": "Charted CKD Stage 3 comorbidity was omitted from billing diagnosis codes. Adds CC severity tier.",
                "financial_impact": f"+${cls.CC_MCC_ADJUSTMENT:,.2f}"
            })
            allowable += cls.CC_MCC_ADJUSTMENT

        # 2. Down-Coding Audit: Type 2 Diabetes (E11.9)
        has_charted_dm = any("diabetes" in c or "t2d" in c or "e11" in c for c in charted_lower)
        has_billed_dm = any(code.startswith("E11") for code in icd_set)
        if has_charted_dm and not has_billed_dm:
            discrepancies.append({
                "type": "DOWN_CODING",
                "code": "E11.9",
                "severity": "LOW",
                "description": "Charted Type 2 Diabetes was omitted from secondary diagnoses."
            })

        # 3. Up-Coding Audit: Heart Failure (I50 series)
        # If heart failure is billed but unmentioned in operative notes or clinical chart
        has_billed_hf = any(code.startswith("I50") for code in icd_set)
        has_substantiated_hf = "heart failure" in operative_notes.lower() or any("heart failure" in c for c in charted_lower)
        if has_billed_hf and not has_substantiated_hf:
            discrepancies.append({
                "type": "UP_CODING",
                "code": "I50.9",
                "severity": "CRITICAL",
                "description": "Congestive Heart Failure (I50) billed on claim without substantiating documentation in chart/operative notes. Payer fraud exposure."
            })

        # 4. Procedure CPT Verification
        if "27130" in cpt_codes and "hip" not in operative_notes.lower():
            discrepancies.append({
                "type": "UP_CODING",
                "code": "27130",
                "severity": "CRITICAL",
                "description": "CPT 27130 (Total Hip) billed but operative note does not describe hip arthroplasty."
            })

        return {
            "discrepancies_found": len(discrepancies) > 0,
            "discrepancies": discrepancies,
            "clean_claim": len(discrepancies) == 0,
            "allowable_reimbursement": allowable
        }
