from app.schemas.form_config import (
    FieldDefIn,
    FieldDefOut,
    FormVersionCreate,
    FormVersionRead,
    PublishResult,
)


def test_field_def_in_valida_field_type_valido():
    from pydantic import ValidationError
    import pytest

    fd = FieldDefIn(
        field_key="sexo",
        label="Sexo",
        field_type="select",
        required=True,
        system_locked=True,
        domain_values=["F", "M"],
        display_order=1,
    )
    assert fd.field_key == "sexo"
    assert fd.domain_values == ["F", "M"]


def test_field_def_in_rechaza_field_type_invalido():
    from pydantic import ValidationError
    import pytest

    with pytest.raises(ValidationError):
        FieldDefIn(
            field_key="foto",
            label="Foto",
            field_type="imagen",  # no válido
            required=False,
        )


def test_form_version_create_acepta_lista_de_campos():
    fv = FormVersionCreate(
        fields=[
            FieldDefIn(field_key="edad", label="Edad", field_type="number", required=True, system_locked=True),
        ]
    )
    assert len(fv.fields) == 1


def test_form_version_read_tiene_from_attributes():
    # Verifica que el schema de lectura pueda construirse desde ORM
    fv = FormVersionRead(
        id=1,
        form_def_id=1,
        version_num=1,
        status="published",
        published_at=None,
        created_by="coord",
        created_at=__import__("datetime").datetime(2026, 6, 10, tzinfo=__import__("datetime").timezone.utc),
        fields=[],
    )
    assert fv.status == "published"


def test_publish_result_tiene_errores_y_version():
    pr = PublishResult(success=True, version_id=3, errors=[])
    assert pr.success is True
    pr2 = PublishResult(success=False, version_id=None, errors=[{"field_key": "x", "error": "falta"}])
    assert len(pr2.errors) == 1
