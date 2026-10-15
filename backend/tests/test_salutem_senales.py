"""Señales de licencia y receta en el formulario de una atención de SALUTEM."""

from app.integrations.salutem.senales import certificado_reposo, registros_receta, tiene_receta

CERTIFICADO = (
    "El médico que suscribe certifica asistir profesionalmente al(la) \r\n<br>paciente X \r\n"
    "<br>quien debe permanecer en reposo desde el\r\n<br>15-04-2024 hasta el ____, "
)


def test_el_certificado_de_reposo_es_una_indicacion_documento():
    contenido = {"indicaciones": [{"tipo": "Documento", "nombre": "Documentos", "registro": CERTIFICADO}]}
    assert certificado_reposo(contenido) is True


def test_un_documento_que_no_habla_de_reposo_no_es_certificado():
    contenido = {"indicaciones": [{"tipo": "Documento", "nombre": "Documentos", "registro": "Certificado de asistencia"}]}
    assert certificado_reposo(contenido) is False


def test_reposo_fuera_de_un_documento_no_cuenta_como_certificado():
    contenido = {"indicaciones": [{"tipo": "Indicación", "nombre": "Indicación General", "registro": "reposo relativo"}]}
    assert certificado_reposo(contenido) is False


def test_receta_medicamentos_con_farmacos_es_receta():
    contenido = {"indicaciones": [{"tipo": "Receta Medicamentos", "nombre": "Receta",
                                   "registro": "Sertralina 50 mg (comprimido)\r\n 1 comprimido al día"}]}
    assert tiene_receta(contenido) is True


def test_el_campo_indicaciones_con_farmacos_es_receta():
    contenido = {"antecedentes": [{"agrupacion": "", "nombre": "Indicaciones",
                                   "registro": "Clotiazepam 5 mg 0-0-1"}]}
    assert tiene_receta(contenido) is True


def test_sin_farmacos_no_hay_receta():
    contenido = {"indicaciones": [{"tipo": "Indicación", "nombre": "Indicación General", "registro": "Control en 15 días"}]}
    assert tiene_receta(contenido) is False
    assert registros_receta(contenido) == []


def test_contenido_vacio_no_tiene_senales():
    assert certificado_reposo({}) is False
    assert tiene_receta({}) is False
