import base64
from typing import Tuple
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature
from src.domain.exceptions import CryptographicSignatureError

class SignatureService:
    """
    Cryptographic signature service enforcing non-repudiation for clinician HITL approvals.
    Uses ECDSA with NIST P-256 (SECP256R1) curve and SHA-256.
    """

    @staticmethod
    def generate_key_pair() -> Tuple[str, str]:
        """Generates a private and public key pair in PEM format."""
        private_key = ec.generate_private_key(ec.SECP256R1())
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode("utf-8")

        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")

        return private_pem, public_pem

    @staticmethod
    def sign_attestation(private_key_pem: str, case_id: str, decision: str, notes: str) -> str:
        """
        Signs the canonical clinical attestation payload:
        payload = '{case_id}:{decision}:{notes}'
        Returns base64 encoded ECDSA signature.
        """
        private_key = serialization.load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
        payload = f"{case_id}:{decision}:{notes}".encode("utf-8")
        signature = private_key.sign(payload, ec.ECDSA(hashes.SHA256())) # type: ignore
        return base64.b64encode(signature).decode("utf-8")

    @staticmethod
    def verify_attestation(public_key_pem: str, case_id: str, decision: str, notes: str, signature_b64: str) -> bool:
        """
        Verifies ECDSA attestation signature against registered clinician public key.
        """
        try:
            public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
            signature_bytes = base64.b64decode(signature_b64)
            payload = f"{case_id}:{decision}:{notes}".encode("utf-8")
            public_key.verify(signature_bytes, payload, ec.ECDSA(hashes.SHA256())) # type: ignore
            return True
        except (InvalidSignature, Exception):
            return False
