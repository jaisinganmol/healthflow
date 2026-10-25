import pytest
import json
from pathlib import Path
from src.infrastructure.persistence.audit_logger import AuditLogger

def test_audit_logger_event_creation(tmp_path: Path):
    log_file = tmp_path / "audit_test.jsonl"
    logger = AuditLogger(log_file_path=log_file)

    payload = {
        "patient_id": "pat-sarah-j",
        "action": "EHR_OBSERVATION_PULL",
        "observations": ["Hemoglobin 11.2", "eGFR 52"]
    }

    record = logger.log_event(
        audit_id="aud-001",
        actor_id="AGENT_CLINICAL_RISK",
        patient_id="pat-sarah-j",
        encounter_id="enc-101",
        action_type="FHIR_READ",
        resource_accessed="Observation/obs-hgb",
        payload=payload,
        clinical_justification="Pre-admission risk assessment for total hip replacement."
    )

    assert record.audit_id == "aud-001"
    assert record.actor_id == "AGENT_CLINICAL_RISK"
    assert len(record.payload_hash) == 64 # SHA-256 hex string

    # Verify log file write
    records = logger.read_records()
    assert len(records) == 1
    assert records[0].payload_hash == record.payload_hash
    assert logger.verify_integrity() is True

def test_audit_logger_tamper_detection(tmp_path: Path):
    log_file = tmp_path / "audit_tamper_test.jsonl"
    logger = AuditLogger(log_file_path=log_file)

    logger.log_event(
        audit_id="aud-002",
        actor_id="DR_SMITH",
        patient_id="pat-sarah-j",
        encounter_id="enc-101",
        action_type="HITL_SIGN_OFF",
        resource_accessed="Encounter/enc-101",
        payload={"decision": "APPROVED"},
        clinical_justification="Attending surgeon clearance."
    )

    # Tamper with file content
    with open(log_file, "r") as f:
        data = json.loads(f.read().strip())
    data["payload_hash"] = "corrupted_hash"
    with open(log_file, "w") as f:
        f.write(json.dumps(data) + "\n")

    assert logger.verify_integrity() is False
