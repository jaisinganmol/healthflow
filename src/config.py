from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # EHR SMART Backend Services Config
    FHIR_BASE_URL: str = "http://localhost:8080/fhir"
    SMART_CLIENT_ID: str = "healthflow-service-client"
    SMART_AUTH_URL: str = "http://localhost:8080/oauth2/token"
    SMART_PRIVATE_KEY_PEM: Optional[str] = None
    SMART_PRIVATE_KEY_PATH: Optional[str] = None

    def get_smart_private_key_pem(self) -> Optional[str]:
        if self.SMART_PRIVATE_KEY_PEM:
            return self.SMART_PRIVATE_KEY_PEM
        if self.SMART_PRIVATE_KEY_PATH:
            from pathlib import Path
            path = Path(self.SMART_PRIVATE_KEY_PATH)
            if path.exists():
                return path.read_text(encoding="utf-8")
        return None
    
    # Twilio Messaging Config
    TWILIO_ACCOUNT_SID: str = "AC_mock_twilio_account_sid_12345"
    TWILIO_AUTH_TOKEN: str = "mock_auth_token_secret_12345"
    TWILIO_PHONE_NUMBER: str = "+15555551234"
    
    # Persistence & Audit
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/healthflow"
    S3_AUDIT_BUCKET: str = "healthflow-audit-trail-worm-dev"
    AWS_REGION: str = "us-east-1"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
