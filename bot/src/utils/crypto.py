from fernet import Fernet


class Crypto:
    def __init__(self, fernet_engine: Fernet):
        self._fernet = fernet_engine

    def cipher_to_str(self, value: str) -> str:
        return self._fernet.encrypt(value).decode()

    def decipher_to_str(self, value: str) -> str:
        return self._fernet.decrypt(value.encode()).decode()
