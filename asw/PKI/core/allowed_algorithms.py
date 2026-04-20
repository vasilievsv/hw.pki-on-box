from __future__ import annotations

from dataclasses import dataclass

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding


_ALLOWED_SIG = {
    "RSA-PSS-SHA256": lambda: (
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    ),
    "RSA-PSS-SHA384": lambda: (
        padding.PSS(mgf=padding.MGF1(hashes.SHA384()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA384(),
    ),
    "ECDSA-SHA256": lambda: (ec.ECDSA(hashes.SHA256()),),
    "ECDSA-SHA384": lambda: (ec.ECDSA(hashes.SHA384()),),
}

_ALLOWED_AEAD = {
    "AES-256-GCM",
}

_FORBIDDEN_SIG = {
    "RSA-PKCS1v15-SHA256",
    "RSA-PKCS1v15-SHA1",
    "RSA-PSS-SHA1",
    "ECDSA-SHA1",
}


@dataclass(frozen=True)
class AllowedSigAlg:
    name: str
    _sign_args: tuple

    @classmethod
    def parse(cls, name: str) -> AllowedSigAlg:
        if name in _FORBIDDEN_SIG:
            raise ValueError(f"Forbidden signature algorithm: {name}")
        factory = _ALLOWED_SIG.get(name)
        if factory is None:
            raise ValueError(
                f"Unknown signature algorithm: {name}. "
                f"Allowed: {sorted(_ALLOWED_SIG)}"
            )
        return cls(name=name, _sign_args=factory())

    @property
    def sign_args(self) -> tuple:
        return self._sign_args

    @property
    def is_rsa(self) -> bool:
        return self.name.startswith("RSA-")

    @property
    def is_ec(self) -> bool:
        return self.name.startswith("ECDSA-")


@dataclass(frozen=True)
class AllowedAead:
    name: str

    @classmethod
    def parse(cls, name: str) -> AllowedAead:
        if name not in _ALLOWED_AEAD:
            raise ValueError(
                f"Unknown AEAD algorithm: {name}. "
                f"Allowed: {sorted(_ALLOWED_AEAD)}"
            )
        return cls(name=name)


RSA_PSS_SHA256 = AllowedSigAlg.parse("RSA-PSS-SHA256")
RSA_PSS_SHA384 = AllowedSigAlg.parse("RSA-PSS-SHA384")
ECDSA_SHA256 = AllowedSigAlg.parse("ECDSA-SHA256")
ECDSA_SHA384 = AllowedSigAlg.parse("ECDSA-SHA384")
AES_256_GCM = AllowedAead.parse("AES-256-GCM")
