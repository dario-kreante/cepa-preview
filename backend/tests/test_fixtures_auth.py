


def test_as_coordinacion_lleva_jwt_de_coordinacion(as_coordinacion):
    r = as_coordinacion.get("/whoami-test")
    assert r.status_code == 200
    assert r.json()["role"] == "Coordinacion"


def test_as_admin_lleva_jwt_de_administrativo(as_admin):
    r = as_admin.get("/whoami-test")
    assert r.status_code == 200
    assert r.json()["role"] == "Administrativo"


def test_as_auditor_lleva_jwt_de_auditor(as_auditor):
    r = as_auditor.get("/whoami-test")
    assert r.status_code == 200
    assert r.json()["role"] == "Auditor"
