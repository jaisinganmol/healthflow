import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from src.workflows.pre_admission import build_pre_admission_graph

@pytest.mark.asyncio
async def test_pre_admission_workflow_interrupt_and_resume():
    checkpointer = MemorySaver()
    app = build_pre_admission_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-sarah-case-001"}}

    # Initial invocation fans out and hits the Tier 2 interrupt checkpoint
    initial_input = {
        "patient_id": "pat-sarah-j",
        "encounter_id": "enc-sarah-001",
        "procedure_cpt": "27130",
        "surgeon_id": "dr-smith-ortho"
    }

    # Run graph until interrupt
    await app.ainvoke(initial_input, config=config)

    # Inspect paused state
    state = await app.aget_state(config)
    assert state.values["scheduling_status"] == "COMPLETED"
    assert state.values["insurance_status"] == "APPROVED"
    assert state.values["clinical_risk_status"] == "COMPLETED"
    assert state.values["risk_tier"] == "TIER_2_REVIEWED"
    assert state.values.get("clearance_finalized") is not True

    # Assert graph is paused at an interrupt task
    assert len(state.tasks) > 0
    interrupt_payload = state.tasks[0].interrupts[0].value
    assert interrupt_payload["tier"] == "TIER_2_REVIEWED"
    assert "CKD" in str(interrupt_payload["flags"])

    # Resume graph with clinician attestation signature
    resume_command = Command(resume={"attestation_signature": "MOCK_ECDSA_DR_ANESTHESIA_SIGNATURE"})
    await app.ainvoke(resume_command, config=config)

    # Verify final completed state
    final_state = await app.aget_state(config)
    assert final_state.values["clearance_finalized"] is True
    assert final_state.values["attestation_signature"] == "MOCK_ECDSA_DR_ANESTHESIA_SIGNATURE"
