import sys
from uuid import uuid4


class SecretStore:
    """No plaintext fallback. Explicitly bind Windows Credential Manager."""

    def _vault(self):
        if sys.platform != "win32":
            raise ValueError("Las credenciales solo están disponibles en el backend nativo Windows")
        from keyring.backends.Windows import WinVaultKeyring

        return WinVaultKeyring()

    def put(self, value: str, ref: str | None = None) -> str:
        ref = ref or str(uuid4())
        self._vault().set_password("OficinaIALocal", ref, value)
        return ref

    def get(self, ref: str | None) -> str:
        if not ref:
            return ""
        result = self._vault().get_password("OficinaIALocal", ref)
        if not result:
            raise ValueError("Credencial no encontrada en Windows Credential Manager")
        return result

    def delete(self, ref: str | None) -> None:
        if ref:
            self._vault().delete_password("OficinaIALocal", ref)


secrets = SecretStore()
