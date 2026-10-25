from fastapi import APIRouter, Request, Form, Response
from typing import Optional
from src.domain.parsers.sms_parser import SMSParser

router = APIRouter(prefix="/api/v1/sms", tags=["Twilio SMS"])

@router.post("/webhook")
async def inbound_sms_webhook(
    From: str = Form(...),
    Body: str = Form(...),
    MessageSid: Optional[str] = Form(None)
) -> Response:
    """
    Inbound Twilio SMS Webhook.
    Extracts scheduling answers or symptom survey replies and responds with TwiML.
    """
    body_text = Body.strip()

    # Check if this is a scheduling slot reply (A, B, C)
    slot = SMSParser.parse_scheduling_selection(body_text)
    if slot:
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>Thank you! Slot option {slot} has been confirmed. Your surgical care team will see you then.</Message>
</Response>"""
        return Response(content=twiml, media_type="application/xml")

    # Check if this is a symptom survey reply
    symptoms = SMSParser.parse_postop_symptoms(body_text)
    pain = symptoms.get("pain_score", 5)
    has_red_flag = symptoms.get("calf_swelling") or symptoms.get("fever_or_drainage") or symptoms.get("shortness_of_breath")

    if has_red_flag:
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>Thank you for reporting. A triage nurse has been notified and will call you shortly. If this is an emergency, call 911 immediately.</Message>
</Response>"""
    else:
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>Recovery check-in received (Pain: {pain}/10). Your progress is on track! Keep resting and stay hydrated.</Message>
</Response>"""

    return Response(content=twiml, media_type="application/xml")
