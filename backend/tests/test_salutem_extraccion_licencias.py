"""Extracción de licencias médicas desde las indicaciones de SALUTEM.

SALUTEM no expone licencias como dato estructurado: aparecen como prosa en
`indicaciones[].registro`, en HTML (visto en QA, empresa 96, 07-09-2026). Con
Pilar (CEPA) se acordó que la indicación traiga días, fecha de inicio, fecha de
término y tipo; mientras eso no esté cargado, los casos de abajo son indicaciones
reales del ambiente de QA, copiadas tal cual (con su HTML, sus errores de tipeo y
sus años equivocados), sin datos que identifiquen a la persona.
"""

from datetime import date

import pytest

from app.integrations.salutem.licencias import ClaseMencion, extraer_licencia

# ── Prórrogas con tipo, reposo, inicio y días ────────────────────────────────


def test_prorroga_con_tipo_reposo_inicio_y_dias():
    registro = (
        "<span>Extiendo licencia médica&nbsp;<b>tipo 6 total&nbsp;</b>desde\r\nel&nbsp;"
        "<b>09/05/2024&nbsp;</b>por&nbsp;<b>21 días</b>, dado por moderado grado de\r\n"
        "discapacidad o interferencia con&nbsp;sus actividades cotidianas, </span>"
        "<span>entre <b>51-60 (EEAG).&nbsp;&nbsp;</b></span>"
    )
    m = extraer_licencia(registro, fecha_atencion=date(2024, 5, 6))

    assert m is not None
    assert m.clase == ClaseMencion.LICENCIA
    assert m.tipo_licencia == "6"
    assert m.extra_sistema is False
    assert m.tipo_reposo == "total"
    assert m.fecha_inicio == date(2024, 5, 9)
    assert m.dias == 21
    # 21 días contando el día de inicio: del 09/05 al 29/05
    assert m.fecha_termino == date(2024, 5, 29)
    assert m.termino_calculado is True
    assert m.avisos == []


def test_prorroga_con_anio_equivocado_se_extrae_pero_avisa():
    """Atención de abril 2024 que dice "desde el 18/04/2023": error de tipeo del médico."""
    registro = (
        "<p><span>Extiendo&nbsp;licencia médica&nbsp;<b>tipo 6 total</b>&nbsp;desde\r\nel "
        "<b>18/04/2023&nbsp;</b>por&nbsp;<b>21 días</b>, dado por moderado grado\r\nde "
        "discapacidad o interferencia con&nbsp;sus actividades cotidianas, </span>"
        "<span>entre <b>51-60 (EEAG). </b></span></p>"
    )
    m = extraer_licencia(registro, fecha_atencion=date(2024, 4, 15))

    assert m is not None
    assert m.fecha_inicio == date(2023, 4, 18)
    assert m.dias == 21
    assert len(m.avisos) == 1
    assert "fecha de inicio" in m.avisos[0].lower()


# ── Licencias extra sistema ──────────────────────────────────────────────────


def test_extrasistema_vigente_hasta_con_anio_de_dos_digitos():
    registro = (
        "<p><span>Paciente se\r\nencuentra con licencia médica extrasistema hasta el "
        "<b>17/04/24,</b> previo a vencimiento se sugiere control médico. <b>&nbsp;EEAG\r\n"
        "55-65</b></span></p>"
    )
    m = extraer_licencia(registro, fecha_atencion=date(2024, 4, 5))

    assert m is not None
    assert m.clase == ClaseMencion.LICENCIA
    assert m.extra_sistema is True
    assert m.tipo_licencia is None
    assert m.fecha_termino == date(2024, 4, 17)
    assert m.termino_calculado is False
    assert m.fecha_inicio is None
    assert m.avisos == []


def test_vencimiento_de_licencia_entre_parentesis():
    registro = (
        "<ol><li>Control\r\nmédico previo a vencimiento de licencia extrasistema "
        "<b>(17/04/2024)</b></li><li><span>Patología\r\nimpresiona de <b>etiología laboral, "
        "</b>se deriva a&nbsp;<b>Estudio de Puesto de Trabajo</b>&nbsp;para investigar "
        "relación causal\r\nentre factores de riesgo laborales y patología actual.</span></li>"
        "<li>Iniciar valoración\r\npor Psicología</li><li>No requiere derivacion psiquiatrica</li></ol>"
    )
    m = extraer_licencia(registro, fecha_atencion=date(2024, 4, 5))

    assert m is not None
    assert m.extra_sistema is True
    assert m.fecha_termino == date(2024, 4, 17)


def test_extra_sistema_separado_y_vigente_hasta_antes_de_la_atencion_avisa():
    """Atención de enero 2025 que dice "vigente hasta el 31/01/2024": año equivocado."""
    registro = (
        "<p><span>Paciente\r\ncon licencia médica extra sistema vigente hasta el "
        "<b>31/01/2024,</b> previo a vencimiento se sugiere control médico</span></p><br>"
    )
    m = extraer_licencia(registro, fecha_atencion=date(2025, 1, 20))

    assert m is not None
    assert m.extra_sistema is True
    assert m.fecha_termino == date(2024, 1, 31)
    assert len(m.avisos) == 1
    assert "fecha de término" in m.avisos[0].lower()


def test_texto_con_errores_de_tipeo_sin_fechas():
    m = extraer_licencia(
        "Paciente se encurntra con licencia media extrasistema&nbsp;",
        fecha_atencion=date(2025, 1, 22),
    )

    assert m is not None
    assert m.clase == ClaseMencion.LICENCIA
    assert m.extra_sistema is True
    assert (m.fecha_inicio, m.fecha_termino, m.dias) == (None, None, None)


# ── Menciones que no son una licencia vigente ───────────────────────────────


@pytest.mark.parametrize(
    ("registro", "fecha_atencion", "reincorporacion"),
    [
        (
            "<p><b>Alta\r\nlaboral Total:</b><span>&nbsp;sin necesidad de\r\nextender licencia "
            "médica dado mejoría en condiciones clínicas y laborales de la\r\npaciente, instando a "
            "incorporación laboral en jornada completa a partir del <b>14/06/2024.</b></span></p>",
            date(2024, 6, 12),
            date(2024, 6, 14),
        ),
        (
            "<p><b>Alta\r\nlaboral Total:</b><span>&nbsp;sin necesidad de\r\nextender licencia "
            "médica dado mejoría progresiva en condiciones clínicas y\r\nlaborales de la paciente, "
            "instando a reincorporación laboral en jornada\r\ncompleta desde el <b>16/02/2025. "
            "</b></span></p>",
            date(2025, 2, 12),
            date(2025, 2, 16),
        ),
    ],
)
def test_alta_laboral_no_es_licencia(registro, fecha_atencion, reincorporacion):
    m = extraer_licencia(registro, fecha_atencion=fecha_atencion)

    assert m is not None
    assert m.clase == ClaseMencion.ALTA_LABORAL
    assert m.fecha_reincorporacion == reincorporacion
    assert (m.tipo_licencia, m.fecha_inicio, m.fecha_termino, m.dias) == (None, None, None, None)


def test_sin_licencia():
    m = extraer_licencia(
        "<p>Paciente se\r\nencuentra sin licencia medica<b></b></p>", fecha_atencion=date(2024, 7, 17)
    )

    assert m is not None
    assert m.clase == ClaseMencion.SIN_LICENCIA


@pytest.mark.parametrize(
    "registro",
    [
        # "Reposo total" sin la palabra licencia no se interpreta como licencia
        "<div>Reposo total.</div><div>Psicoterapia.</div><div>Fármacos.</div>"
        "<div>Control con psicóloga</div><div>Control médico en 15 días<br></div>",
        "Sertralina 50 mg: 1 comprimido cada mañana por 30 días Zopiclona 7,5 mg: 1 comprimido "
        "cada noche por 30 días",
        # sugerencia a futuro, no un alta: el médico todavía no la da
        "<p><span>Control médico en 15 días o SOS. Considerar alta laboral total No requiere "
        "derivación psiquiátrica. Continuidad a tratamiento psicológico.</span></p>",
        # indicaciones de exámenes llegan como dict, no como texto
        {"tipos": {"1024": {"nombre": "HEMATOLOGICOS", "examenes": {"13873": "03.01.045 HEMOGRAMA"}}}},
        "",
        None,
    ],
)
def test_indicaciones_sin_licencia_devuelven_none(registro):
    assert extraer_licencia(registro, fecha_atencion=date(2025, 1, 22)) is None


# ── Formato acordado con Pilar (07-09-2026) ──────────────────────────────────


def test_formato_acordado_con_campos_explicitos():
    registro = (
        "<p>Días de licencia: 15</p><p>Fecha de inicio: 01/09/2026</p>"
        "<p>Fecha de término: 15/09/2026</p><p>Tipo de licencia: 6 total</p>"
    )
    m = extraer_licencia(registro, fecha_atencion=date(2026, 9, 1))

    assert m is not None
    assert m.clase == ClaseMencion.LICENCIA
    assert m.dias == 15
    assert m.fecha_inicio == date(2026, 9, 1)
    assert m.fecha_termino == date(2026, 9, 15)
    assert m.termino_calculado is False
    assert m.tipo_licencia == "6"
    assert m.tipo_reposo == "total"
    assert m.avisos == []


def test_formato_acordado_avisa_si_dias_y_fechas_no_cuadran():
    registro = (
        "Días de licencia: 10\nFecha de inicio: 01/09/2026\n"
        "Fecha de término: 15/09/2026\nTipo de licencia: extra sistema"
    )
    m = extraer_licencia(registro, fecha_atencion=date(2026, 9, 1))

    assert m is not None
    assert m.extra_sistema is True
    assert m.tipo_licencia is None
    assert m.fecha_termino == date(2026, 9, 15)
    assert len(m.avisos) == 1
    assert "días" in m.avisos[0].lower()
