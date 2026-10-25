from typing import Dict, Any, Tuple
from src.domain.models.triage import TriageEvaluation

class PostOpTriageRules:
    """
    Evaluates post-discharge patient-reported symptoms against procedure-specific baseline trajectories.
    Specifically calibrated for CPT 27130 (Total Hip Arthroplasty) across POD 1, 3, and 7.
    """

    @staticmethod
    def evaluate_recovery_trajectory(
        cpt_code: str,
        pod_day: int,
        symptoms: Dict[str, Any]
    ) -> TriageEvaluation:
        pain = symptoms.get("pain_score", 5)

        # 1. Critical Red Flag Triaging (Immediate Emergency / High Risk)
        if symptoms.get("shortness_of_breath"):
            return TriageEvaluation(
                pod_day=pod_day,
                risk_level="HIGH_RISK",
                nurse_escalation_required=True,
                clinical_rationale="EMERGENCY: Shortness of breath reported post-op. Rule out pulmonary embolism.",
                recommended_patient_message="We have alerted our triage team immediately. Please sit upright, rest, and expect a call from our nurse within 5 minutes. If severe, dial 911."
            )

        if symptoms.get("calf_swelling"):
            return TriageEvaluation(
                pod_day=pod_day,
                risk_level="HIGH_RISK",
                nurse_escalation_required=True,
                clinical_rationale="URGENT: Calf pain or lower extremity swelling reported. Rule out deep vein thrombosis (DVT).",
                recommended_patient_message="Thank you for reporting. Calf swelling requires direct nursing evaluation. A triage nurse will phone you within 15 minutes."
            )

        if symptoms.get("fever_or_drainage"):
            return TriageEvaluation(
                pod_day=pod_day,
                risk_level="HIGH_RISK",
                nurse_escalation_required=True,
                clinical_rationale="URGENT: Surgical site infection concern: fever, redness, or drainage reported.",
                recommended_patient_message="Incision redness/fever reported. We have notified your surgical care team for direct outreach."
            )

        # 2. Procedure Trajectory Norms (CPT 27130 Total Hip)
        if pod_day == 1:
            # Expected norm: pain 4-7
            if pain <= 7:
                return TriageEvaluation(
                    pod_day=pod_day,
                    risk_level="LOW_RISK",
                    nurse_escalation_required=False,
                    clinical_rationale=f"Pain score {pain}/10 is within expected POD 1 range (4-7). No acute red flags.",
                    recommended_patient_message=f"Recovery is right on track for Day 1 (Pain: {pain}/10). Take pain medication as prescribed and rest. We will check in again on Day 3."
                )
            else:
                return TriageEvaluation(
                    pod_day=pod_day,
                    risk_level="MODERATE_RISK",
                    nurse_escalation_required=True,
                    clinical_rationale=f"Pain score {pain}/10 exceeds expected POD 1 range (4-7). Oral analgesia adjustment needed.",
                    recommended_patient_message=f"Pain score of {pain}/10 is higher than anticipated. A nurse will follow up today to review your pain control medications."
                )

        elif pod_day == 3:
            # Expected norm: pain 3-5
            if pain <= 5:
                return TriageEvaluation(
                    pod_day=pod_day,
                    risk_level="LOW_RISK",
                    nurse_escalation_required=False,
                    clinical_rationale=f"Pain score {pain}/10 is within expected POD 3 range (3-5). Mobility improving.",
                    recommended_patient_message=f"Great progress on Day 3! Pain {pain}/10 is expected. Continue your walking exercises and hydration."
                )
            else:
                return TriageEvaluation(
                    pod_day=pod_day,
                    risk_level="MODERATE_RISK",
                    nurse_escalation_required=True,
                    clinical_rationale=f"Pain score {pain}/10 exceeds expected POD 3 norm (3-5).",
                    recommended_patient_message="Your pain is slightly elevated for Day 3. Our nursing team will reach out to ensure you have adequate pain management."
                )

        elif pod_day >= 7:
            # Expected norm: pain 1-3
            if pain <= 3:
                return TriageEvaluation(
                    pod_day=pod_day,
                    risk_level="LOW_RISK",
                    nurse_escalation_required=False,
                    clinical_rationale=f"Pain score {pain}/10 is within expected POD 7 norm (1-3). Incision healing well.",
                    recommended_patient_message="1-week milestone reached! Recovery is progressing smoothly. Keep up the physical therapy."
                )
            else:
                return TriageEvaluation(
                    pod_day=pod_day,
                    risk_level="MODERATE_RISK",
                    nurse_escalation_required=True,
                    clinical_rationale=f"Pain score {pain}/10 exceeds expected POD 7 norm (1-3).",
                    recommended_patient_message="You are reporting persistent pain above normal 1-week levels. A clinician will call to evaluate."
                )

        # Fallback routine evaluation
        return TriageEvaluation(
            pod_day=pod_day,
            risk_level="LOW_RISK",
            nurse_escalation_required=False,
            clinical_rationale=f"Routine check-in on POD {pod_day}. Symptoms stable.",
            recommended_patient_message="Check-in recorded. Keep recovering!"
        )
