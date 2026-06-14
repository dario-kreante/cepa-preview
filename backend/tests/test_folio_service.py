from app.services.folio import folio_existe, siguiente_folio


def test_folios_secuenciales_consecutivos(db_session):
    f1 = siguiente_folio(db_session)
    f2 = siguiente_folio(db_session)
    db_session.flush()
    # mismo año, secuencia +1
    assert f1 != f2
    num1 = int(f1.split("-")[-1])
    num2 = int(f2.split("-")[-1])
    assert num2 == num1 + 1


def test_formato_folio(db_session):
    f = siguiente_folio(db_session)
    # formato F-<anio>-<correlativo de 4+ dígitos>
    partes = f.split("-")
    assert partes[0] == "F"
    assert len(partes[1]) == 4  # año
    assert partes[2].isdigit()


def test_folio_existe_detecta_colision(db_session):
    from app.models.ingreso import Ingreso
    from app.models.paciente import Paciente

    p = Paciente(rut="111111111", nombre="Test", sexo="F", edad=30, region="Maule")
    db_session.add(p)
    db_session.flush()
    ing = Ingreso(
        paciente_id=p.id,
        folio="F-2026-9999",
        folio_manual=True,
        fecha_ingreso=__import__("datetime").date(2026, 6, 10),
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="x",
        estado="activo",
    )
    db_session.add(ing)
    db_session.flush()
    assert folio_existe(db_session, "F-2026-9999") is True
    assert folio_existe(db_session, "F-2026-0001") is False
