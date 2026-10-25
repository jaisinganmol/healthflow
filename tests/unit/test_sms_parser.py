import pytest
from src.domain.parsers.sms_parser import SMSParser

def test_parse_scheduling_selection_variations():
    assert SMSParser.parse_scheduling_selection("A") == "A"
    assert SMSParser.parse_scheduling_selection("b") == "B"
    assert SMSParser.parse_scheduling_selection("Option C") == "C"
    assert SMSParser.parse_scheduling_selection("Please book slot B.") == "B"
    assert SMSParser.parse_scheduling_selection("Hello, I want choice A") == "A"
    assert SMSParser.parse_scheduling_selection("No option works") is None

def test_parse_postop_symptoms_structured():
    # Canonical structured format from deep dive: "5, no, no, no, no"
    res = SMSParser.parse_postop_symptoms("5, no, no, no, no")
    assert res["pain_score"] == 5
    assert res["fever_or_drainage"] is False
    assert res["calf_swelling"] is False
    assert res["shortness_of_breath"] is False
    assert res["nausea_or_vomiting"] is False

def test_parse_postop_symptoms_with_calf_swelling():
    res = SMSParser.parse_postop_symptoms("6, no, yes, no, no")
    assert res["pain_score"] == 6
    assert res["fever_or_drainage"] is False
    assert res["calf_swelling"] is True
    assert res["shortness_of_breath"] is False

def test_parse_postop_symptoms_natural_language():
    nl_text = "My pain is 3 out of 10. No fever or redness. Leg is fine but feeling slightly nauseous."
    res = SMSParser.parse_postop_symptoms(nl_text)
    assert res["pain_score"] == 3
    assert res["fever_or_drainage"] is False
    assert res["calf_swelling"] is False
    assert res["nausea_or_vomiting"] is True
