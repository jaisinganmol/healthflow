from typing import Optional, Dict, Any
import structlog
from src.config import settings

logger = structlog.get_logger()

class TwilioClient:
    """
    Twilio SMS integration client.
    Handles outbound SMS dispatch and inbound signature validation.
    Runs in simulated mock mode when test credentials are configured.
    """
    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_number: Optional[str] = None
    ):
        self.account_sid = account_sid or settings.TWILIO_ACCOUNT_SID
        self.auth_token = auth_token or settings.TWILIO_AUTH_TOKEN
        self.from_number = from_number or settings.TWILIO_PHONE_NUMBER
        self.is_mock = self.account_sid.startswith("AC_mock")

    async def send_sms(self, to_phone: str, message: str) -> Dict[str, Any]:
        """Dispatches an outbound SMS to a patient."""
        if self.is_mock:
            logger.info("mock_twilio_sms_dispatched", to=to_phone, body=message)
            return {
                "sid": f"SM_mock_{abs(hash(message))}",
                "status": "delivered",
                "to": to_phone,
                "body": message
            }

        # Production Twilio SDK invocation
        from twilio.rest import Client
        client = Client(self.account_sid, self.auth_token)
        msg = client.messages.create(
            to=to_phone,
            from_=self.from_number,
            body=message
        )
        return {
            "sid": msg.sid,
            "status": msg.status,
            "to": to_phone,
            "body": message
        }

    def validate_signature(self, url: str, post_params: Dict[str, str], signature: str) -> bool:
        """Validates incoming Twilio webhook authenticity via HMAC-SHA1."""
        if self.is_mock:
            return True # Allow webhook in dev/test
        from twilio.request_validator import RequestValidator
        validator = RequestValidator(self.auth_token)
        return validator.validate(url, post_params, signature)
