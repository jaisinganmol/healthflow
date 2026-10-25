# HealthFlow AI - Production Healthcare Orchestration Engine

HealthFlow AI compresses hospital pre-admission clearance from **55–60 hours down to ~30 minutes** by executing scheduling, insurance verification, and clinical risk evaluation in parallel rather than in sequence. Following discharge, it proactively watches patient recovery via conversational two-way Twilio SMS across Post-Op Days (POD) 1, 3, and 7—evaluating reported symptoms against procedure-specific recovery trajectories and individual baselines, with a strict clinician gate protecting patient safety.

---

## Architecture Topology

```mermaid
flowchart TD
    subgraph PreOp["Pre-Admission Clearance Pipeline (LangGraph)"]
        AdmitOrder["Surgeon Order in EHR<br/>(CPT 27130 / Multi-Patient Live EHR)"] --> FanOut["Concurrent Fan-Out"]
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

1. **Vendor-Agnostic FHIR R4 Integration:** Standardizes directly on FHIR R4 resources (`Patient`, `Condition`, `Observation`, `MedicationStatement`, `MedicationRequest`, `AllergyIntolerance`, `Procedure`, `DocumentReference`) using SMART Backend Services (asymmetric JWT RS384 OAuth2). Connects directly to Epic, Cerner, Athenahealth, and Medidata without proprietary adapter rewrites.
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
├── epic_private_key.pem               # RSA 2048 private key for SMART Backend Services OAuth2
├── epic_public_key.pem                # Matching RSA public key registered with open.epic.com
├── scripts/
│   ├── simulate_journey.py            # Turnkey CLI End-to-End Patient Journey Simulator
│   └── test_epic_cohort.py            # Multi-Patient Live Epic on FHIR Test Runner
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
│   │   │   ├── fhir.py                # Normalized Pydantic models for FHIR R4 resources
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
│   │   │   ├── factory.py             # Dynamic EHR client factory (Mock vs SMART FHIR)
│   │   │   ├── mock_client.py         # Synthea bundle fixture reader
│   │   │   └── fhir_client.py         # SMART Backend Services OAuth2 client (RS384 JWT)
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
│       ├── routes_events.py           # Admission, discharge & patient search endpoints
│       ├── routes_twilio.py           # Inbound 2-way SMS webhook
│       └── routes_hitl.py             # Clinician review & cryptographic resume API
├── frontend/                          # Next.js 14 Responsive Web Application
│   ├── app/                           # App router pages (Clinician Portal, SMS Sim, Coding Audit)
│   ├── components/                    # Tailored Tailwind CSS clinical components
│   └── package.json
└── tests/
    ├── fixtures/synthea/
    │   └── sarah_johnson.json         # Curated Synthea FHIR bundle (Sarah Johnson case)
    ├── eval/
    │   └── test_clinical_benchmarks.py# 100-patient synthetic cohort & fail-closed benchmarks
    ├── unit/
    │   ├── test_fhir_client.py        # FHIR R4 schema, raw Epic normalization & search tests
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

## Step 1: Environment Setup & Installation

### Prerequisites
* Python 3.12+ (or 3.13/3.14)
* Node.js 18+ (for frontend portal)
* `uv` (recommended) or `pip`

### 1.1 Clone and Set Up Virtual Environment
```bash
cd /Users/anmoljaising/healthflow

# Create virtual environment and install all dependencies in editable mode
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### 1.2 Environment Configuration ([`.env`](file:///Users/anmoljaising/healthflow/.env))
Create or adjust your `.env` file in the project root:
```env
# Runtime Environment (development | staging | production)
ENVIRONMENT=development
LOG_LEVEL=INFO

# Epic on FHIR Sandbox Configuration (SMART Backend Services)
FHIR_BASE_URL=https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4
SMART_AUTH_URL=https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token
SMART_CLIENT_ID=your_epic_client_id_here
SMART_PRIVATE_KEY_PATH=/Users/anmoljaising/healthflow/epic_private_key.pem

# Twilio SMS Gateway Configuration (Mock or Live)
TWILIO_ACCOUNT_SID=AC_mock_twilio_account_sid_12345
TWILIO_AUTH_TOKEN=mock_auth_token_secret_12345
TWILIO_PHONE_NUMBER=+15555551234

# Persistence & HIPAA Compliance
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/healthflow
S3_AUDIT_BUCKET=healthflow-audit-trail-worm-dev
AWS_REGION=us-east-1
```

---

## Step 2: Testing Modes

HealthFlow AI supports two complementary testing modes:
1. **Offline / Synthetic Testing:** Immediate end-to-end simulation using curated Synthea clinical bundles.
2. **Live Multi-Patient Testing:** Dynamic query against real Epic on FHIR sandbox endpoints with your Epic Developer Account credentials.

---

### Option A: Run the Turnkey Patient Journey Simulator (Offline / Synthea)

Run the end-to-end patient journey simulator without needing external network access or running servers:
```bash
.venv/bin/python scripts/simulate_journey.py
```

This executes all 6 stages of the clinical journey in sequence:
1. **Canonical FHIR Extraction:** Loads Sarah Johnson's Synthea record (67yo female with CKD 3a and osteoarthritis).
2. **Parallel Pre-Admission Fan-Out:** Concurrently triggers OR scheduling, EDI 270/278 insurance pre-authorization, and FHIR clinical risk calculation.
3. **Hierarchical Clinical Gate:** Detects age 67, CKD 3a comorbidity, and Metformin/Aspirin holds, computing a risk score of 6.0 and automatically pausing at a **Tier 2 (Moderate Risk)** `interrupt()` checkpoint.
4. **Attending Cryptographic Sign-Off:** Signs the case with Attending Anesthesiologist ECDSA NIST P-256 digital signature, verifies the signature, and resumes the clearance workflow.
5. **Two-Way Twilio SMS Processing:** Simulates the patient confirming slot "B" and sending post-op day check-in updates.
6. **Post-Discharge Triage & Revenue Cycle Audit:** Triages POD 1 vitals and catches unbilled CKD 3a (preventing $3,800 in lost DRG revenue) with full SHA-256 append-only tamper-detection verification.

---

### Option B: Test with Multiple Dynamic Patients from Epic on FHIR

If you have an **Epic Developer Account** on [open.epic.com](https://open.epic.com), you can test HealthFlow against **multiple live patients** dynamically.

#### 1. Configure Your Epic Backend Services App
1. Go to [open.epic.com](https://open.epic.com) and log into your Developer Account.
2. Under **Build Apps**, create or edit your app:
   - App Type: **Backend Systems (Non-Interactive)**
   - Target System: **Open Sandbox**
   - Upload Public Key: Provide the contents of [`epic_public_key.pem`](file:///Users/anmoljaising/healthflow/epic_public_key.pem) located in the project root.
   - Required FHIR R4 Scopes: Enable `Patient.Search (R4)`, `Patient.Read (R4)`, `Condition.Search (R4)`, `Observation.Search (R4)`, `MedicationRequest.Search (R4)`, and `Flag.Create (R4)`.
3. Copy your assigned **Non-Production Client ID** into `.env`:
   ```env
   ENVIRONMENT=staging
   SMART_CLIENT_ID=your_epic_non_prod_client_id
   ```

#### 2. Run the Multi-Patient Cohort Evaluator CLI

Because Epic requires demographic filters rather than a blank `GET /Patient` query, HealthFlow allows you to query multiple live patients using family search or sandbox identifiers:

```bash
# Query multiple patients by family name:
.venv/bin/python scripts/test_epic_cohort.py --family Lopez
.venv/bin/python scripts/test_epic_cohort.py --family Smith
.venv/bin/python scripts/test_epic_cohort.py --family Lin

# Query standard Epic open sandbox test patient cohort:
.venv/bin/python scripts/test_epic_cohort.py --use-sandbox-defaults

# Query specific Epic Patient IDs:
.venv/bin/python scripts/test_epic_cohort.py --patient-ids \
  Tbt3KuCDeD6u69JFaKkgugw3 \
  erXuFYUfucBZaryVpgxafGW5FsXUeg5HzobbRnP1wh-3M3 \
  eq081-VQEgP8FsdtnuZTq1w3
```

#### What `test_epic_cohort.py` does:
1. Mints an RS384 asymmetric JWT assertion and exchanges it for an OAuth2 bearer token from Epic.
2. Queries Epic's live FHIR R4 API for each patient's demographics, active diagnoses, lab panels, and active medications.
3. Automatically normalizes nested Epic arrays (`HumanName`, `identifier` MRN, `telecom`, `MedicationRequest`).
4. Calculates ASA Physical Status, Revised Cardiac Risk Index (RCRI), and active clinical flags.
5. Assigns each patient to their deterministic clearance tier: **Tier 1 (Auto-Clear)**, **Tier 2 (HITL Clinician Gate)**, or **Tier 3 (Escalation Panel)**.

---

### Option C: Run the Full Automated Test Suite & Clinical Benchmarks

Execute all 25 unit, integration, and clinical evaluation tests:
```bash
.venv/bin/pytest tests/ -v
```

All 25 tests pass deterministically in under 0.5s:
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
tests/unit/test_fhir_client.py::test_raw_epic_fhir_r4_normalization PASSED
tests/unit/test_fhir_client.py::test_search_patients_mock PASSED
tests/unit/test_hitl.py::test_signature_generation_and_verification PASSED
tests/unit/test_hitl.py::test_hitl_resume_api_flow PASSED
tests/unit/test_sms_parser.py::test_parse_scheduling_selection_variations PASSED
tests/unit/test_sms_parser.py::test_parse_postop_symptoms_structured PASSED
tests/unit/test_sms_parser.py::test_parse_postop_symptoms_with_calf_swelling PASSED
tests/unit/test_sms_parser.py::test_parse_postop_symptoms_natural_language PASSED
tests/unit/test_triage_rules.py::test_total_hip_pod1_normal PASSED
tests/unit/test_triage_rules.py::test_total_hip_pod1_calf_swelling_dvt_alert PASSED
tests/unit/test_triage_rules.py::test_total_hip_pod7_milestone PASSED

============================== 25 passed in 0.38s ==============================
```

---

## Step 3: Starting the Application Servers

### 3.1 Start the FastAPI Backend
Start the application server with Uvicorn:
```bash
.venv/bin/uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend is accessible at `http://localhost:8000`:
* **Interactive OpenAPI Swagger Docs:** `http://localhost:8000/docs`
* **Health Endpoint:** `http://localhost:8000/health`

### 3.2 Start the Next.js Frontend Portal
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view:
* **Clinician Review Dashboard:** Review paused Tier 2 clearance cases and review structured clinical risk flags.
* **Cryptographic Attestation Portal:** Register attending clinician public keys and submit ECDSA signatures.
* **Patient Twilio SMS Simulator:** Interactive two-way SMS terminal for OR slot confirmation and post-op symptom surveys.
* **Revenue Cycle Auditor:** Dual-direction ICD-10 / CPT discrepancy inspector.

---

## Step 4: Step-by-Step API Walkthrough with `curl`

### 4.1 Search Live Patients from EHR
Query multiple patient records dynamically:
```bash
curl "http://localhost:8000/api/v1/events/patients/search?family=Lopez&limit=5"
```
**Response:**
```json
{
  "count": 1,
  "patients": [
    {
      "resourceType": "Patient",
      "id": "erXuFYUfucBZaryVpgxafGW5FsXUeg5HzobbRnP1wh-3M3",
      "mrn": "E10002",
      "name": "Camilla Lopez",
      "birthDate": "1984-07-04",
      "gender": "female",
      "telecom_phone": "+15555551234"
    }
  ]
}
```

---

### 4.2 Ingest a Pre-Admission Surgical Order
Trigger the pre-admission clearance pipeline. Scheduling, insurance pre-auth, and clinical risk evaluation run concurrently:
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
**Response:**
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

### 4.3 Clinician Review & ECDSA Digital Sign-Off (Resume Checkpoint)

1. **View pending paused cases:**
```bash
curl http://localhost:8000/api/v1/cases/pending
```

2. **Generate and register clinician keypair:**
```python
from src.infrastructure.security.signatures import SignatureService
private_pem, public_pem = SignatureService.generate_key_pair()
sig = SignatureService.sign_attestation(
    private_pem,
    "enc-sarah-101",
    "APPROVED",
    "Proceed under hip arthroplasty protocol. Hold Metformin 24h pre-op."
)
```

3. **Register public key:**
```bash
curl -X POST http://localhost:8000/api/v1/cases/register-key \
  -H "Content-Type: application/json" \
  -d '{
    "clinician_id": "dr-anesthesiologist-01",
    "public_key_pem": "'"$PUBLIC_KEY_PEM"'"
  }'
```

4. **Resume clearance workflow with cryptographic signature:**
```bash
curl -X POST http://localhost:8000/api/v1/cases/enc-sarah-101/resume \
  -H "Content-Type: application/json" \
  -d '{
    "clinician_id": "dr-anesthesiologist-01",
    "attestation_decision": "APPROVED",
    "clinical_notes": "Proceed under hip arthroplasty protocol. Hold Metformin 24h pre-op.",
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

### 4.4 Conversational Two-Way Twilio SMS Webhook
Simulate an inbound patient SMS selecting OR slot "B":
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

### 4.5 Post-Discharge Triage & Revenue Cycle Discrepancy Audit
Trigger Post-Op Day 1 follow-up with Sarah's SMS update (`"5, no, no, no, no"`):
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

### 4.6 Verify the Immutable HIPAA Audit Trail
Inspect the append-only log on disk:
```bash
cat data/audit_log.jsonl | jq .
```
Verify SHA-256 tamper-evident integrity programmatically:
```python
from src.infrastructure.persistence.audit_logger import AuditLogger
logger = AuditLogger()
assert logger.verify_integrity() is True
print("✓ Audit log verified: Zero tamper detected across all records.")
```

---

## Step 5: Containerization & Cloud Deployment

### 5.1 Build Minimal Distroless Docker Container
```bash
docker build -t healthflow-ai:0.1.0 .
docker run -p 8000:8000 --env-file .env healthflow-ai:0.1.0
```

### 5.2 Deploy to Kubernetes via Kustomize
```bash
kubectl apply -k infra/k8s/
```

### 5.3 Progressive Blue/Green Delivery with ArgoCD Rollouts
```bash
kubectl argo rollouts status rollout healthflow-ai-rollout -n healthflow
kubectl argo rollouts promote healthflow-ai-rollout -n healthflow
```

### 5.4 Statutory HIPAA Infrastructure (Terraform)
```bash
cd infra/terraform
terraform init
terraform plan
terraform apply
```
Provisions:
* **Amazon S3 Object Lock in COMPLIANCE Mode:** Statutory 6-year (2,190 days) immutable retention lock; cannot be deleted or shortened by any IAM role or root account.
* **AWS SQS FIFO Queues:** KMS-encrypted, content-based deduplication for EHR events.
* **AWS Aurora PostgreSQL Cluster:** Encrypted cluster backing LangGraph's durable checkpointer.

---

## License
Proprietary & Confidential - Built for production healthcare environments.
