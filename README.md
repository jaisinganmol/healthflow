# HealthFlow AI - Production Healthcare Orchestration Engine

HealthFlow AI compresses hospital pre-admission clearance from **55–60 hours down to ~30 minutes** by executing scheduling, insurance verification, and clinical risk evaluation in parallel rather than in sequence. Following discharge, it proactively watches patient recovery via conversational two-way Twilio SMS across Post-Op Days (POD) 1, 3, and 7—evaluating reported symptoms against procedure-specific recovery trajectories and individual baselines, with a strict clinician gate protecting patient safety.

---

## Architecture Topology

```mermaid
flowchart TD
    subgraph PreOp["Pre-Admission Clearance Pipeline (LangGraph)"]
        AdmitOrder["Surgeon Order in EHR<br/>(CPT 27130 / Sarah Johnson)"] --> FanOut["Concurrent Fan-Out"]
        FanOut --> Sched["Scheduling Agent<br/>(OR Slots + SMS Intake)"]
        FanOut --> Ins["Insurance Agent<br/>(270/278 + Backoff Retry)"]
        FanOut --> Risk["Clinical Risk Agent<br/>(FHIR R4: ASA, RCRI, Contraindications)"]
        
        Sched --> JoinBarrier{"Strict Join Barrier<br/>(All Branches Resolved)"}
        Ins --> JoinBarrier
        Risk --> JoinBarrier
        
        JoinBarrier --> ClinicalGate["Hierarchical Clinical Gate Evaluator"]
        ClinicalGate -->|Score 0-1| AutoClear["Tier 1: Automated Commit to EHR"]
        ClinicalGate -->|Score 2-4| HITLPause["Tier 2: Reviewed (interrupt Checkpoint)"]
        ClinicalGate -->|Score >=5| EscalateHalt["Tier 3: Escalated (Multi-Disc Panel)"]
    end

    subgraph PostOp["Post-Discharge Recovery & Revenue Cycle"]
        DischargeEvent["Discharge Event"] --> PostFanOut["Post-Op Concurrency"]
        PostFanOut --> DP["Discharge Planning Agent<br/>(Stability Vitals Check)"]
        PostFanOut --> FT["Follow-Up Triage Agent<br/>(POD 1, 3, 7 Check-in vs Baseline)"]
        PostFanOut --> BC["Billing & Coding Agent<br/>(Dual-Direction Discrepancy Audit)"]
    end

    subgraph StorageCompliance["Persistence & Statutory HIPAA Compliance"]
        HITLPause <--> Checkpointer[("LangGraph Checkpointer / Aurora")]
        FT <--> TwilioGateway["Twilio SMS Gateway"]
        AllAgents["All Pipeline Events"] --> AuditLogger["Immutable Audit Logger"]
        AuditLogger --> S3WORM[("AWS S3 Object Lock<br/>(COMPLIANCE Mode - 6-Year Retention)")]
    end
```

---

## Key Clinical & Engineering Specifications

1. **Vendor-Agnostic FHIR R4 Integration:** Standardizes directly on FHIR R4 resources (`Patient`, `Condition`, `Observation`, `MedicationStatement`, `AllergyIntolerance`, `Procedure`, `DocumentReference`) using SMART Backend Services (asymmetric JWT OAuth2). Works across Epic, Cerner, Athenahealth, and Medidata without proprietary adapter rewrites.
2. **Fail-Closed Missing Data Contract:** Zero inference or hallucinated assumptions over absent clinical data. If required pre-op observations or lab panels are missing, the system strictly halts and triggers an escalation alert.
3. **Hierarchical Clinical Gate:** Computes ASA Physical Status, Revised Cardiac Risk Index (RCRI), patient age, and active contraindication flags (Anemia, CKD 3a, Metformin hold, Aspirin bleed risk, and VTE prophylaxis).
4. **Non-Repudiable Cryptographic Sign-Off:** Attending clinician sign-offs on Tier 2 cases require ECDSA (NIST P-256 / SHA-256) digital signatures verified before checkpoint resumption.
5. **Two-Way Conversational Twilio SMS:** Direct 2-way SMS check-ins for slot selection and post-op symptom tracking with token and compound negation NLP extraction.
6. **Dual-Direction Discrepancy Audit:** Analyzes operative documentation and ICD-10/CPT pairings to prevent both *down-coding* (unbilled CKD 3a comorbidity resulting in lost hospital reimbursement) and *up-coding* (unsubstantiated heart failure billing creating Medicare fraud exposure).
7. **Statutory 6-Year Immutable Audit Trail:** Emits structured audit records with SHA-256 payload hashes to tamper-evident storage and AWS S3 Object Lock in Compliance Mode.

---

## Directory Structure

```
healthflow/
├── .github/workflows/ci.yml           # Automated CI/CD (Ruff, Bandit, Pytest, Docker Build)
├── pyproject.toml                     # Modern dependencies (FastAPI, LangGraph, Pydantic v2, Twilio)
├── Dockerfile                         # Multi-stage minimal distroless Python 3.12 container
├── scripts/
│   └── simulate_journey.py            # Turnkey CLI End-to-End Patient Journey Simulator
├── infra/
│   ├── k8s/                           # Production Kubernetes & ArgoCD GitOps manifests
│   │   ├── deployment.yaml            # Distroless container deployment with non-root securityContext
│   │   ├── rollout.yaml               # ArgoCD Rollout Blue/Green progressive delivery
│   │   ├── service.yaml               # ClusterIP routing
│   │   ├── ingress.yaml               # TLS termination & HIPAA security headers
│   │   ├── hpa.yaml                   # HorizontalPodAutoscaler (CPU & memory)
│   │   ├── configmap.yaml             # Environment configuration
│   │   ├── secret.yaml                # Production secrets template
│   │   └── kustomization.yaml         # Kustomize manifest bundle
│   └── terraform/                     # Production HIPAA infrastructure declarations
│       ├── main.tf                    # S3 WORM Object Lock, SQS FIFO queues, Aurora PostgreSQL
│       └── variables.tf
├── src/
│   ├── config.py                      # Pydantic BaseSettings
│   ├── domain/
│   │   ├── exceptions.py              # Domain exceptions (MissingClinicalDataException, etc.)
│   │   ├── models/
│   │   │   ├── fhir.py                # Pydantic models for FHIR R4 resources
│   │   │   ├── clinical.py            # RiskProfile, ClinicalFlag, RiskTier enum
│   │   │   ├── triage.py              # SymptomReport, TriageEvaluation
│   │   │   └── audit.py               # AuditRecord with SHA-256 payload hashing
│   │   ├── parsers/
│   │   │   └── sms_parser.py          # Two-way Twilio SMS regex & NLP negation parser
│   │   └── rules/
│   │       ├── clinical_gate.py       # Deterministic ASA/RCRI scoring & tier gating
│   │       ├── triage_rules.py        # POD 1, 3, 7 recovery norms vs DVT/infection alerts
│   │       └── coding_rules.py        # Dual-direction ICD-10 / CPT discrepancy engine
│   ├── infrastructure/
│   │   ├── ehr/
│   │   │   ├── base.py                # Abstract EHRClient interface
│   │   │   ├── mock_client.py         # Synthea bundle fixture reader
│   │   │   └── fhir_client.py         # SMART Backend Services OAuth2 client
│   │   ├── messaging/
│   │   │   └── twilio_client.py       # Twilio REST client & signature validator
│   │   ├── persistence/
│   │   │   └── audit_logger.py        # Append-only audit logger (S3 Object Lock / local JSONL)
│   │   └── security/
│   │       └── signatures.py          # ECDSA NIST P-256 keygen, signing & verification
│   ├── workflows/
│   │   ├── state.py                   # PreOpState and PostOpState TypedDicts
│   │   ├── pre_admission.py           # Pre-op fan-out/join graph with interrupt()
│   │   └── post_discharge.py          # Post-op triage & billing audit graph
│   └── api/
│       ├── main.py                    # FastAPI root application
│       ├── routes_events.py           # Admission & discharge webhook receivers
│       ├── routes_twilio.py           # Inbound 2-way SMS webhook
│       └── routes_hitl.py             # Clinician review & cryptographic resume API
└── tests/
    ├── fixtures/synthea/
    │   └── sarah_johnson.json         # Curated Synthea FHIR bundle (Sarah Johnson case)
    ├── eval/
    │   └── test_clinical_benchmarks.py# 100-patient synthetic cohort & fail-closed benchmarks
    ├── unit/
    │   ├── test_fhir_client.py        # FHIR R4 schema & fail-closed tests
    │   ├── test_clinical_gate.py      # ASA/RCRI scoring & gating tests
    │   ├── test_sms_parser.py         # NLP symptom parsing & negation tests
    │   ├── test_hitl.py               # ECDSA signature verification & resume tests
    │   ├── test_triage_rules.py       # POD 1/3/7 baseline & red flag alert tests
    │   ├── test_coding_rules.py       # Up-coding & down-coding audit tests
    │   └── test_audit_logger.py       # SHA-256 tamper-detection tests
    └── integration/
        ├── test_pre_admission.py      # LangGraph fan-out, interrupt & resume test
        └── test_e2e_flow.py           # Full end-to-end patient journey integration test
```

---

## Quickstart & Installation

### Prerequisites
* Python 3.12+
* `uv` (recommended) or `pip`

### 1. Set Up Virtual Environment & Dependencies
```bash
cd /Users/anmoljaising/healthflow

# Create venv and install all dependencies in editable mode with dev tools
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### 2. Run the Interactive Patient Journey Simulator
Experience the full end-to-end patient lifecycle without starting external servers:
```bash
.venv/bin/python scripts/simulate_journey.py
```
This executes all 6 stages of the clinical journey in sequence:
1. Canonical FHIR R4 extraction from Synthea records.
2. Concurrent pre-admission clearance fan-out (OR scheduling, EDI 270/278 verification, clinical risk scoring).
3. Hierarchical Clinical Gate pause at Tier 2 (`interrupt()` checkpoint).
4. Attending anesthesiologist ECDSA NIST P-256 cryptographic sign-off & checkpoint resume.
5. Inbound Twilio 2-way SMS parsing for OR slot confirmation and post-op symptom surveys.
6. Post-discharge triage, dual-direction coding discrepancy audit, and SHA-256 tamper-evident WORM audit verification.

### 3. Run the Automated Test Suite & Clinical Benchmarks
Execute all 23 unit, integration, and clinical evaluation tests:
```bash
.venv/bin/pytest tests/ -v
```

All 23 tests pass in under 0.5s:
```
tests/eval/test_clinical_benchmarks.py::test_fail_closed_contract_on_missing_observations PASSED
tests/eval/test_clinical_benchmarks.py::test_clinical_gate_cohort_regression_benchmark PASSED
tests/eval/test_clinical_benchmarks.py::test_postop_triage_trajectory_benchmark PASSED
tests/integration/test_e2e_flow.py::test_end_to_end_sarah_johnson_journey PASSED
tests/integration/test_pre_admission.py::test_pre_admission_workflow_interrupt_and_resume PASSED
tests/unit/test_audit_logger.py::test_audit_logger_event_creation PASSED
tests/unit/test_audit_logger.py::test_audit_logger_tamper_detection PASSED
tests/unit/test_clinical_gate.py::test_sarah_johnson_tier_2_routing PASSED
tests/unit/test_clinical_gate.py::test_healthy_young_patient_tier_1 PASSED
tests/unit/test_coding_rules.py::test_down_coding_detection_ckd PASSED
tests/unit/test_coding_rules.py::test_up_coding_detection_unsupported_heart_failure PASSED
tests/unit/test_coding_rules.py::test_clean_claim PASSED
tests/unit/test_fhir_client.py::test_mock_ehr_sarah_johnson_extraction PASSED
tests/unit/test_fhir_client.py::test_missing_clinical_data_fail_closed PASSED
tests/unit/test_hitl.py::test_signature_generation_and_verification PASSED
tests/unit/test_hitl.py::test_hitl_resume_api_flow PASSED
tests/unit/test_sms_parser.py::test_parse_scheduling_selection_variations PASSED
tests/unit/test_sms_parser.py::test_parse_postop_symptoms_structured PASSED
tests/unit/test_sms_parser.py::test_parse_postop_symptoms_with_calf_swelling PASSED
tests/unit/test_sms_parser.py::test_parse_postop_symptoms_natural_language PASSED
tests/unit/test_triage_rules.py::test_total_hip_pod1_normal PASSED
tests/unit/test_triage_rules.py::test_total_hip_pod1_calf_swelling_dvt_alert PASSED
tests/unit/test_triage_rules.py::test_total_hip_pod7_milestone PASSED

======================== 23 passed in 0.38s =========================
```

---

## Starting the Application Server & Web Frontend

### 1. Start the FastAPI Backend
Start the FastAPI application with Uvicorn:
```bash
.venv/bin/uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend will be available at `http://localhost:8000`. You can inspect the interactive OpenAPI documentation at:
* **Swagger UI:** `http://localhost:8000/docs`
* **Health Check:** `http://localhost:8000/health`

### 2. Start the Responsive Next.js Web Frontend (Vercel-Ready)
In a separate terminal, start the Next.js frontend:
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) to access the interactive Clinician Review Portal, Patient SMS Simulator, and Revenue Cycle Auditor.

#### Deploying Frontend to Vercel:
```bash
cd frontend
npx vercel
```

---

## Step-by-Step API Walkthrough with `curl`

### Step 1: Ingest an Admission Surgical Order (Sarah Johnson)
Trigger the pre-admission clearance pipeline. Scheduling, insurance verification, and clinical risk evaluation run concurrently:
```bash
curl -X POST http://localhost:8000/api/v1/events/admission \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "pat-sarah-j",
    "encounter_id": "enc-sarah-101",
    "procedure_cpt": "27130",
    "surgeon_id": "dr-smith-ortho"
  }'
```
**Response:** The graph detects Sarah's age (67), CKD 3a comorbidity, and drug holds, evaluating to **Tier 2 (Moderate Risk)** and safely pausing at an `interrupt()` checkpoint:
```json
{
  "encounter_id": "enc-sarah-101",
  "status": "PAUSED_AT_CHECKPOINT",
  "risk_tier": "TIER_2_REVIEWED",
  "risk_score": 6.0,
  "scheduling_status": "COMPLETED",
  "insurance_status": "APPROVED",
  "clinical_risk_status": "COMPLETED",
  "flags": [
    {"code": "FLAG_1_MILD_ANEMIA", "severity": "MODERATE"},
    {"code": "FLAG_2_CKD_STAGE_3A", "severity": "HIGH"},
    {"code": "FLAG_3_METFORMIN_PREOP_HOLD", "severity": "MODERATE"},
    {"code": "FLAG_4_ASPIRIN_BLEED_RISK", "severity": "MODERATE"},
    {"code": "FLAG_5_HIGH_VTE_PROTOCOL", "severity": "HIGH"}
  ],
  "summary": "Moderate surgical risk (Score 6.0, ASA 2, RCRI 1, 5 flags). Paused for attending physician review."
}
```

---

### Step 2: Clinician Review & Cryptographic Sign-Off (Resume Checkpoint)

1. View pending cases awaiting clinician review:
```bash
curl http://localhost:8000/api/v1/cases/pending
```

2. Generate an ECDSA P-256 key pair (or register the physician's public key):
```python
from src.infrastructure.security.signatures import SignatureService
private_pem, public_pem = SignatureService.generate_key_pair()
sig = SignatureService.sign_attestation(private_pem, "enc-sarah-101", "APPROVED", "Proceed under hip arthroplasty protocol.")
```

3. Register the clinician's public key:
```bash
curl -X POST http://localhost:8000/api/v1/cases/register-key \
  -H "Content-Type: application/json" \
  -d '{
    "clinician_id": "dr-anesthesiologist-01",
    "public_key_pem": "'"$PUBLIC_KEY_PEM"'"
  }'
```

4. Resume the paused clearance case with the valid digital signature:
```bash
curl -X POST http://localhost:8000/api/v1/cases/enc-sarah-101/resume \
  -H "Content-Type: application/json" \
  -d '{
    "clinician_id": "dr-anesthesiologist-01",
    "attestation_decision": "APPROVED",
    "clinical_notes": "Proceed under hip arthroplasty protocol.",
    "signature_base64": "'"$SIGNATURE_B64"'"
  }'
```
**Response:**
```json
{
  "case_id": "enc-sarah-101",
  "status": "CLEARED",
  "clearance_committed_to_ehr": true,
  "clinician_id": "dr-anesthesiologist-01"
}
```

---

### Step 3: Conversational Two-Way Twilio SMS Webhook

Simulate a patient confirming their OR time slot:
```bash
curl -X POST http://localhost:8000/api/v1/sms/webhook \
  -d "From=+15551234567" \
  -d "Body=B"
```
**TwiML Response:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>Thank you! Slot option B has been confirmed. Your surgical care team will see you then.</Message>
</Response>
```

---

### Step 4: Post-Discharge Recovery Triage & Billing Discrepancy Audit

Trigger the Post-Op Day 1 check-in (simulating Sarah's text `"5, no, no, no, no"`):
```bash
curl -X POST http://localhost:8000/api/v1/events/discharge \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "pat-sarah-j",
    "encounter_id": "enc-sarah-101",
    "cpt_code": "27130",
    "pod_day": 1,
    "patient_sms_response": "5, no, no, no, no"
  }'
```
**Response:**
```json
{
  "encounter_id": "enc-sarah-101",
  "pod_day": 1,
  "discharge_cleared": true,
  "triage_risk_level": "LOW_RISK",
  "nurse_escalation_required": false,
  "triage_notes": "Pain score 5/10 is within expected POD 1 range (4-7). No acute red flags.",
  "clean_claim": false,
  "discrepancies": [
    {
      "type": "DOWN_CODING",
      "code": "N18.30",
      "severity": "MODERATE",
      "description": "Charted CKD Stage 3 comorbidity was omitted from billing diagnosis codes. Adds CC severity tier.",
      "financial_impact": "+$3,800.00"
    }
  ],
  "allowable_reimbursement": 18000.0
}
```

---

### Step 5: Verify the Immutable HIPAA Audit Trail

HealthFlow writes an append-only audit entry with SHA-256 payload hashing for every clinical event. Inspect the log on disk:
```bash
cat data/audit_log.jsonl | jq .
```
Verify log integrity programmatically:
```python
from src.infrastructure.persistence.audit_logger import AuditLogger
logger = AuditLogger()
assert logger.verify_integrity() is True
```

---

## Containerization & Kubernetes GitOps Deployment

### 1. Build and Run via Docker
Build the minimal multi-stage distroless image:
```bash
docker build -t healthflow-ai:0.1.0 .
docker run -p 8000:8000 --env-file .env healthflow-ai:0.1.0
```

### 2. Deploy to Kubernetes via Kustomize
Deploy the entire production stack (Deployment, ArgoCD Rollout, Services, Ingress, HPA, ConfigMaps, Secrets):
```bash
kubectl apply -k infra/k8s/
```

### 3. Progressive Delivery with ArgoCD Rollouts
Monitor the blue/green deployment status:
```bash
kubectl argo rollouts status rollout healthflow-ai-rollout -n healthflow
kubectl argo rollouts promote healthflow-ai-rollout -n healthflow
```

---

## Production Infrastructure (Terraform)

Deploy statutory HIPAA infrastructure to AWS:
```bash
cd infra/terraform
terraform init
terraform plan
terraform apply
```
This provisions:
1. **Amazon S3 Object Lock in Compliance Mode:** Statutory 6-year (2,190 days) immutable retention lock; cannot be deleted or shortened by any IAM role or root user.
2. **AWS SQS FIFO Queues:** KMS-encrypted, content-based deduplication for admission and discharge event ingestion.
3. **AWS Aurora PostgreSQL Cluster:** Encrypted PostgreSQL cluster backing LangGraph's durable checkpointer.

---

## License
Proprietary & Confidential - Built for production healthcare environments.
