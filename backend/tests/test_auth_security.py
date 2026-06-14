from app.auth.security import hash_password, verify_password


def test_hash_no_es_la_clave_en_claro():
    hashed = hash_password("Secreto123")
    assert hashed != "Secreto123"
    assert len(hashed) > 20


def test_verify_password_acepta_clave_correcta():
    hashed = hash_password("Secreto123")
    assert verify_password("Secreto123", hashed) is True


def test_verify_password_rechaza_clave_incorrecta():
    hashed = hash_password("Secreto123")
    assert verify_password("otra-clave", hashed) is False
