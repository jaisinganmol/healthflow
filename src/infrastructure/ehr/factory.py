from typing import Optional
from pathlib import Path
from src.config import settings
from src.infrastructure.ehr.base import EHRClient
from src.infrastructure.ehr.mock_client import MockEHRClient
from src.infrastructure.ehr.fhir_client import FHIRRestClient

def get_ehr_client(bundle_path: Optional[Path] = None, force_mock: bool = False) -> EHRClient:
    """
    Dynamic EHR Client Factory.
    - Uses MockEHRClient for development, offline test suites, and CI/CD pipelines.
    - Uses FHIRRestClient with SMART Backend Services OAuth2 for staging, sandbox, and production.
    """
    if force_mock or settings.ENVIRONMENT in ["development", "test", "local"]:
        return MockEHRClient(bundle_path=bundle_path)

    return FHIRRestClient(
        base_url=settings.FHIR_BASE_URL,
        client_id=settings.SMART_CLIENT_ID,
        auth_url=settings.SMART_AUTH_URL,
        private_key_pem=settings.get_smart_private_key_pem()
    )
