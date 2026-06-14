from pwdlib import PasswordHash

_password_hash = PasswordHash.recommended()


def hash_password(plain: str) -> str:
    """Devuelve el hash (argon2) de una contraseña en claro."""
    return _password_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica una contraseña en claro contra su hash almacenado."""
    return _password_hash.verify(plain, hashed)
