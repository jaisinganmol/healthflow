class HealthFlowException(Exception):
    """Base exception for HealthFlow domain errors."""
    pass

class MissingClinicalDataException(HealthFlowException):
    """Raised when an essential clinical parameter is absent from the EHR payload, enforcing fail-closed contract."""
    pass

class EHRConnectionError(HealthFlowException):
    """Raised when communication with the EHR fails."""
    pass

class InvalidFHIRPayloadException(HealthFlowException):
    """Raised when an incoming FHIR payload violates FHIR R4 schema invariants."""
    pass

class CryptographicSignatureError(HealthFlowException):
    """Raised when a clinician HITL attestation signature fails cryptographic validation."""
    pass

class PayerPreAuthError(HealthFlowException):
    """Raised when payer insurance clearinghouse fails or is unreachable after backoff."""
    pass
