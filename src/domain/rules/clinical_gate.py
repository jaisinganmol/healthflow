from typing import List, Tuple, Set
from src.domain.models.fhir import FHIRPatient, FHIRCondition, FHIRObservation, FHIRMedicationStatement
from src.domain.models.clinical import RiskTier, ClinicalFlag

class ClinicalGateEngine:
    """
    Deterministic hierarchical clinical gating engine.
    Evaluates ASA score, RCRI score, age, and clinical contraindication flags.
    """

    @staticmethod
    def calculate_asa(conditions: List[FHIRCondition], age: int) -> int:
        """
        Computes ASA Physical Status classification (1 to 6).
        ASA 1: Healthy normal patient.
        ASA 2: Mild to moderate systemic disease (controlled hypertension, T2D, CKD 3a, age >= 65).
        ASA 3: Severe systemic disease with significant functional limitation (CKD 4+, severe CHF).
        ASA 4: Severe systemic disease that is a constant threat to life.
        """
        condition_texts = [
            (c.code.text or "").lower() + " " + " ".join(cod.display.lower() for cod in c.code.coding if cod.display)
            for c in conditions
        ]
        
        has_end_stage_disease = any(
            "end stage" in txt or "ckd stage 4" in txt or "ckd stage 5" in txt or "severe heart failure" in txt
            for txt in condition_texts
        )
        if has_end_stage_disease:
            return 3

        has_systemic_disease = any(
            "hypertension" in txt or "diabetes" in txt or "dyslipidemia" in txt or "osteoarthritis" in txt or "ckd" in txt or "chronic kidney" in txt
            for txt in condition_texts
        )
        if has_systemic_disease or age >= 65:
            return 2

        return 1

    @staticmethod
    def calculate_rcri(cpt: str, conditions: List[FHIRCondition], labs: List[FHIRObservation]) -> int:
        """
        Computes Revised Cardiac Risk Index (RCRI) score (0 to 6):
        1. High-risk surgery (e.g. major orthopedic arthroplasty)
        2. History of ischemic heart disease
        3. History of congestive heart failure
        4. History of cerebrovascular disease
        5. Preoperative treatment with insulin
        6. Preoperative serum creatinine > 2.0 mg/dL
        """
        score = 0
        condition_texts = [
            (c.code.text or "").lower() + " " + " ".join(cod.display.lower() for cod in c.code.coding if cod.display)
            for c in conditions
        ]

        # 1. High risk surgery: Total Hip (27130), Total Knee (27447)
        if cpt in ["27130", "27447"]:
            score += 1

        # 2. Ischemic heart disease
        if any("ischemic" in txt or "coronary" in txt or "myocardial infarction" in txt for txt in condition_texts):
            score += 1

        # 3. Congestive heart failure
        if any("heart failure" in txt or "chf" in txt for txt in condition_texts):
            score += 1

        # 4. Cerebrovascular disease
        if any("stroke" in txt or "tia" in txt or "cerebrovascular" in txt for txt in condition_texts):
            score += 1

        # 5. Serum creatinine > 2.0 mg/dL
        for obs in labs:
            obs_text = (obs.code.text or "").lower()
            codes = [cod.code for cod in obs.code.coding]
            if ("creatinine" in obs_text or "2160-0" in codes) and obs.valueQuantity_value and obs.valueQuantity_value > 2.0:
                score += 1

        return score

    @staticmethod
    def evaluate_flags(
        patient: FHIRPatient,
        conditions: List[FHIRCondition],
        labs: List[FHIRObservation],
        meds: List[FHIRMedicationStatement],
        cpt: str
    ) -> List[ClinicalFlag]:
        flags: List[ClinicalFlag] = []
        flag_codes_seen: Set[str] = set()

        # Flag 1: Mild Anemia (Hb < 12.0 g/dL)
        for obs in labs:
            code_str = (obs.code.text or "").lower()
            codes = [cod.code for cod in obs.code.coding]
            if ("hemoglobin" in code_str or "718-7" in codes) and obs.valueQuantity_value and obs.valueQuantity_value < 12.0:
                if "FLAG_1_MILD_ANEMIA" not in flag_codes_seen:
                    flags.append(ClinicalFlag(
                        code="FLAG_1_MILD_ANEMIA",
                        name="Mild Pre-Op Anemia",
                        severity="MODERATE",
                        action_required=f"Hemoglobin {obs.valueQuantity_value} g/dL below 12.0: Type & screen, cross-match blood order."
                    ))
                    flag_codes_seen.add("FLAG_1_MILD_ANEMIA")

        # Flag 2: CKD Stage 3a (eGFR 45-59 mL/min)
        for obs in labs:
            code_str = (obs.code.text or "").lower()
            codes = [cod.code for cod in obs.code.coding]
            if ("egfr" in code_str or "33914-3" in codes or "glomerular" in code_str) and obs.valueQuantity_value and 45 <= obs.valueQuantity_value <= 59:
                if "FLAG_2_CKD_STAGE_3A" not in flag_codes_seen:
                    flags.append(ClinicalFlag(
                        code="FLAG_2_CKD_STAGE_3A",
                        name="CKD Stage 3a",
                        severity="HIGH",
                        action_required="Moderate renal impairment (eGFR 52): Avoid NSAIDs and contrast dye; anesthesiologist consult required."
                    ))
                    flag_codes_seen.add("FLAG_2_CKD_STAGE_3A")

        # Flag 3: Metformin Pre-Op Hold
        for m in meds:
            med_text = (m.medicationCodeableConcept.text or "").lower() + " " + m.dosage_text.lower()
            if "metformin" in med_text:
                if "FLAG_3_METFORMIN_PREOP_HOLD" not in flag_codes_seen:
                    flags.append(ClinicalFlag(
                        code="FLAG_3_METFORMIN_PREOP_HOLD",
                        name="Metformin Hold Protocol",
                        severity="MODERATE",
                        action_required="Hold Metformin 24 hours pre-op to prevent lactic acidosis; implement glucose monitoring."
                    ))
                    flag_codes_seen.add("FLAG_3_METFORMIN_PREOP_HOLD")

        # Flag 4: Aspirin Bleed Risk
        for m in meds:
            med_text = (m.medicationCodeableConcept.text or "").lower() + " " + m.dosage_text.lower()
            if "aspirin" in med_text:
                if "FLAG_4_ASPIRIN_BLEED_RISK" not in flag_codes_seen:
                    flags.append(ClinicalFlag(
                        code="FLAG_4_ASPIRIN_BLEED_RISK",
                        name="Aspirin Bleed Risk",
                        severity="MODERATE",
                        action_required="Aspirin active: Surgeon confirmation required on hold vs. continue decision."
                    ))
                    flag_codes_seen.add("FLAG_4_ASPIRIN_BLEED_RISK")

        # Flag 5: High VTE Surgery (Only for major orthopedic arthroplasty)
        if cpt in ["27130", "27447"]:
            flags.append(ClinicalFlag(
                code="FLAG_5_HIGH_VTE_PROTOCOL",
                name="VTE Prophylaxis Required",
                severity="HIGH",
                action_required="Total Hip Arthroplasty is high VTE risk: Mandate pneumatic compression devices and anticoagulation protocol."
            ))

        return flags

    @classmethod
    def evaluate_case(
        cls,
        patient: FHIRPatient,
        conditions: List[FHIRCondition],
        labs: List[FHIRObservation],
        meds: List[FHIRMedicationStatement],
        cpt: str = "27130"
    ) -> Tuple[float, RiskTier, List[ClinicalFlag], str]:
        asa = cls.calculate_asa(conditions, patient.age)
        rcri = cls.calculate_rcri(cpt, conditions, labs)
        flags = cls.evaluate_flags(patient, conditions, labs, meds, cpt)

        # Composite score calculation:
        # ASA (weight 1.0) + RCRI (weight 1.0) + Age Score (weight 0.5) + Flag penalty (0.5 each)
        age_score = 0.0 if patient.age < 65 else (1.0 if patient.age <= 75 else 2.0)
        flag_points = len(flags) * 0.5
        composite_score = round((asa * 1.0) + (rcri * 1.0) + (age_score * 0.5) + flag_points, 2)

        # Critical contraindications force Tier 3
        has_critical_flag = any(f.severity == "CRITICAL" for f in flags)
        if asa >= 4 or rcri >= 3 or composite_score >= 8.5 or has_critical_flag:
            tier = RiskTier.TIER_3_ESCALATED
            summary = f"High surgical risk (Score {composite_score}, ASA {asa}, RCRI {rcri}). Reassigned to multidisciplinary panel."
        elif asa >= 2 or rcri >= 1 or patient.age >= 65 or len(flags) >= 1:
            tier = RiskTier.TIER_2_REVIEWED
            summary = f"Moderate surgical risk (Score {composite_score}, ASA {asa}, RCRI {rcri}, {len(flags)} flags). Paused for attending physician review."
        else:
            tier = RiskTier.TIER_1_AUTO
            summary = f"Low routine surgical risk (Score {composite_score}, ASA {asa}, RCRI {rcri}). Automated clearance approved."

        return composite_score, tier, flags, summary
