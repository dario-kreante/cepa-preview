/**
 * Contenido de la página de Ayuda (COMP-2609-01).
 *
 * Una guía por pantalla del menú, con la ruta como id: así el ícono (?) del Topbar abre
 * la guía de la pantalla en la que está el usuario (`/ayuda?guia=/licencias`).
 * Los textos citan las etiquetas tal como se ven en la UI; si cambia un botón, cambia aquí.
 */
import type { Rol } from "@/lib/rbac";

export type Tono = "success" | "warning" | "destructive" | "info" | "neutral" | "purple";

export interface Etiqueta {
  texto: string;
  tono: Tono;
  significado: string;
}

export interface Tarea {
  titulo: string;
  pasos: string[];
}

export interface Guia {
  /** Ruta de la pantalla; también es el id de la guía. */
  ruta: string;
  titulo: string;
  resumen: string;
  tareas: Tarea[];
  etiquetas?: Etiqueta[];
  /** Lo que llega solo desde SALUTEM, para que nadie lo ingrese dos veces. */
  automatico?: string;
  consejos?: string[];
  /** Quién puede registrar o modificar (si no se indica, Coordinación y Administrativo). */
  quienEscribe?: string;
}

export const GUIAS: Guia[] = [
  {
    ruta: "/",
    titulo: "Dashboard",
    resumen:
      "Resumen de la actividad del período y de lo que queda por gestionar hoy. Es solo de consulta.",
    tareas: [
      {
        titulo: "Revisar lo pendiente del día",
        pasos: [
          "Elige el período con «7 días», «30 días» o «90 días», o escribe «Desde» y «Hasta» y presiona «Aplicar».",
          "Mira la sección «Por gestionar hoy»: las tarjetas con borde rojo tienen algo que atender.",
          "Haz clic en una tarjeta (por ejemplo «Sin folio» u «ODA vencidas») para ir directo al módulo.",
        ],
      },
    ],
    etiquetas: [
      { texto: "—", tono: "neutral", significado: "La cifra aún está cargando o no se pudo leer. No significa cero." },
    ],
    automatico:
      "Atenciones, inasistencias y anulaciones se calculan con la copia de SALUTEM, que se actualiza sola.",
    consejos: ["El período queda en la dirección de la página: puedes copiarla y compartirla con tu equipo."],
  },
  {
    ruta: "/ingresos",
    titulo: "Ingresos y pacientes",
    resumen: "Busca pacientes, abre su ficha completa y crea ingresos nuevos.",
    tareas: [
      {
        titulo: "Buscar un paciente",
        pasos: [
          "Escribe en el buscador del menú lateral («Buscar paciente…») y presiona Enter, o usa el buscador de esta pantalla.",
          "Puedes buscar por RUT, folio, parte del nombre o ID SALUTEM.",
          "Haz clic en una fila para abrir la ficha con sus pestañas «Resumen», «Licencias», «Fármacos», «Controles», «ODA» y «SALUTEM».",
        ],
      },
      {
        titulo: "Crear un ingreso",
        pasos: [
          "Presiona «Nuevo ingreso».",
          "Completa RUT, nombre, edad, región, diagnóstico, fecha de ingreso, sexo, tipo de derivación y tipo de ingreso.",
          "Presiona «Crear ingreso». El folio se asigna solo (formato F-2026-0001) y el ingreso queda activo.",
        ],
      },
    ],
    etiquetas: [
      { texto: "Falta folio", tono: "warning", significado: "Paciente atendido en SALUTEM que aún no tiene ingreso en el SIGE. Usa «Completar registro»." },
      { texto: "SALUTEM", tono: "info", significado: "Dato creado automáticamente desde una atención en SALUTEM." },
    ],
    automatico:
      "Las atenciones de la pestaña SALUTEM llegan solas. El botón «Importar desde SALUTEM» sirve solo para forzar una actualización.",
    consejos: [
      "Solo el perfil Administrativo puede corregir el folio (botón «Editar» en la tarjeta Folio). El cambio se aplica también a los reingresos.",
      "Si el buscador del menú no aparece, expande el menú lateral: se oculta cuando está colapsado.",
    ],
  },
  {
    ruta: "/pendientes-folio",
    titulo: "Pendientes de folio",
    resumen:
      "Pacientes que se atendieron en SALUTEM y todavía no tienen ingreso en el SIGE. El número rojo del menú indica cuántos quedan.",
    tareas: [
      {
        titulo: "Completar el registro de un paciente",
        pasos: [
          "Presiona «Completar registro» en la fila del paciente.",
          "Revisa los datos que vienen precargados y completa los que faltan.",
          "Presiona «Crear ingreso». El paciente sale de la lista y su alerta se cierra sola.",
        ],
      },
      {
        titulo: "Descartar a alguien que no es paciente del CEPA",
        pasos: [
          "Presiona «Descartar».",
          "Escribe el motivo (es obligatorio y queda registrado).",
          "Confirma con «Descartar paciente».",
        ],
      },
    ],
    automatico:
      "La sincronización crea la fila y la alerta «Paciente nuevo pendiente de folio» por cada persona atendida en SALUTEM que no existe en el SIGE.",
  },
  {
    ruta: "/licencias",
    titulo: "Licencias médicas",
    resumen: "Historial de licencias de cada paciente, registro de licencias nuevas, anulaciones y envío al ISL.",
    tareas: [
      {
        titulo: "Registrar una licencia",
        pasos: [
          "Busca al paciente por RUT, folio, nombre o ID SALUTEM y selecciónalo.",
          "Presiona «Nueva licencia».",
          "Completa tipo de licencia, tipo de reposo, fechas, cantidad de días y diagnóstico.",
          "Presiona «Registrar licencia».",
        ],
      },
      {
        titulo: "Marcar licencias como enviadas al ISL",
        pasos: [
          "Marca la casilla de cada licencia enviada.",
          "Presiona «Envío masivo ISL»: quedan como «Enviado» con la fecha de hoy.",
          "Para una sola licencia o para un rechazo, usa el ícono «Actualizar envío ISL» de su fila.",
        ],
      },
    ],
    etiquetas: [
      { texto: "Vigente", tono: "success", significado: "La licencia está en curso." },
      { texto: "Vence en 2d", tono: "destructive", significado: "Quedan menos de 3 días." },
      { texto: "Vence en 5d", tono: "warning", significado: "Quedan menos de 7 días." },
      { texto: "Finalizada", tono: "neutral", significado: "Ya pasó la fecha de término." },
      { texto: "Anulada", tono: "destructive", significado: "Se anuló con un motivo. No se puede deshacer." },
      { texto: "Pendiente", tono: "warning", significado: "Aún no se envía al ISL." },
    ],
    automatico:
      "Cuando un médico indica una licencia en SALUTEM, llega la alerta «Licencia emitida en control» con los datos sugeridos. No se registra sola: revísala y presiona «Registrar licencia».",
    consejos: ["Anular es irreversible y pide justificación. Si solo hay un error de fechas, corrige en vez de anular."],
  },
  {
    ruta: "/farmacos",
    titulo: "Gestión de fármacos",
    resumen: "Registro farmacológico de cada paciente: esquema de indicaciones, recetas y seguimiento del tratamiento.",
    tareas: [
      {
        titulo: "Registrar una receta",
        pasos: [
          "Busca al paciente y selecciónalo.",
          "Si dice «Sin registro farmacológico», presiona «Crear registro» e indica el médico tratante.",
          "Presiona «Nueva receta», completa medicamento y fechas de emisión y revisión.",
          "Presiona «Guardar receta».",
        ],
      },
      {
        titulo: "Aprovechar lo recetado en SALUTEM",
        pasos: [
          "Revisa el panel «Fármacos recetados en SALUTEM».",
          "Usa «Agregar al esquema» o «Registrar receta» en cada fármaco que corresponda.",
        ],
      },
    ],
    etiquetas: [
      { texto: "Vigente", tono: "success", significado: "La fecha de revisión aún no llega." },
      { texto: "Por vencer", tono: "warning", significado: "La revisión es dentro de los próximos 5 días." },
      { texto: "Vencida", tono: "destructive", significado: "La fecha de revisión ya pasó." },
      { texto: "Extra sistema", tono: "purple", significado: "Indicado fuera del CEPA." },
    ],
    automatico:
      "Los fármacos recetados en SALUTEM aparecen como sugerencias junto con la alerta «Receta emitida en control». Ninguno se registra solo.",
  },
  {
    ruta: "/controles",
    titulo: "Controles médicos",
    resumen: "Controles de cada paciente: fecha, próximo control, licencia, RECA y evaluación clínica.",
    tareas: [
      {
        titulo: "Registrar un control a mano",
        pasos: [
          "Busca al paciente y selecciónalo.",
          "Presiona «Nuevo control», elige la fecha y el médico tratante (o «Otro» si no está en el catálogo).",
          "Presiona «Guardar control». La semana del tratamiento se calcula sola.",
        ],
      },
      {
        titulo: "Completar un control",
        pasos: [
          "Usa los botones de la fila: «Próximo control», «Licencia/RECA» o «Evaluación».",
          "Despliega la flecha junto a la fecha para ver el detalle clínico. Bajo la tabla están los «Documentos del paciente en SALUTEM»; las licencias y recetas también se ven en sus módulos.",
        ],
      },
    ],
    etiquetas: [
      { texto: "SALUTEM", tono: "info", significado: "Control creado solo desde una atención médica en SALUTEM. No lo ingreses de nuevo." },
      { texto: "Agendado", tono: "success", significado: "El próximo control ya tiene hora." },
    ],
    automatico:
      "Cada atención médica realizada en SALUTEM crea su control con fecha, médico, licencia, reposo y GAF. El estado RECA siempre lo completa el CEPA.",
    consejos: ["Si «Ver» no abre el documento, permite las ventanas emergentes en el navegador."],
  },
  {
    ruta: "/ept",
    titulo: "Seguimiento EPT",
    resumen: "Evaluaciones de Puesto de Trabajo: proceso, plazos y contactos con empleadores e ISL.",
    tareas: [
      {
        titulo: "Crear un caso EPT",
        pasos: [
          "Busca al trabajador y selecciónalo.",
          "Presiona «Nueva EPT» y completa mes, fecha de ingreso, región, factor de riesgo y si corresponde EPT.",
          "Después registra el «Proceso EPT» y los «Plazos EPT» desde el caso.",
        ],
      },
      {
        titulo: "Abrir un caso existente",
        pasos: ["Escribe el número en «Cargar caso N°» y presiona «Cargar», o entra desde su alerta."],
      },
    ],
    etiquetas: [
      { texto: "En plazo", tono: "info", significado: "Aún hay tiempo." },
      { texto: "Por vencer", tono: "warning", significado: "El plazo está cerca." },
      { texto: "Vencido", tono: "destructive", significado: "El plazo ya pasó." },
      { texto: "Cumplido", tono: "success", significado: "Se entregó a tiempo." },
    ],
    quienEscribe: "Solo el perfil Administrativo. Coordinación puede consultar.",
    automatico: "Cada mañana se generan las alertas «Plazo informe EPT» y «Plazo portal ISL».",
  },
  {
    ruta: "/reintegro",
    titulo: "Seguimiento reintegro",
    resumen: "Reintegro laboral: caso, RECA, medidas correctivas y cierre con altas.",
    tareas: [
      {
        titulo: "Crear y cerrar un caso",
        pasos: [
          "Busca al paciente, selecciónalo y presiona «Nuevo caso».",
          "Registra la RECA desde el panel «RECA y medidas correctivas».",
          "Al terminar, presiona «Reintegro / cierre», indica el estado, las altas y presiona «Guardar cierre».",
        ],
      },
    ],
    etiquetas: [
      { texto: "Pendiente", tono: "info", significado: "Aún no se reintegra." },
      { texto: "Parcial", tono: "warning", significado: "Reintegro parcial." },
      { texto: "Total", tono: "success", significado: "Reintegro completo." },
    ],
    consejos: ["La fecha de reintegro no puede ser anterior a la fecha de la RECA ni a la del caso."],
  },
  {
    ruta: "/auditoria",
    titulo: "Auditoría",
    resumen: "Vista consolidada de un caso completo y reportes para auditoría. Solo de consulta.",
    tareas: [
      {
        titulo: "Revisar un caso",
        pasos: [
          "En «Vista de caso», elige buscar por RUT, folio o N° siniestro y presiona «Buscar».",
          "Haz clic en el resultado para ver evaluaciones, controles y cierre en una sola página.",
        ],
      },
      {
        titulo: "Descargar un reporte",
        pasos: ["En «Reportes», indica «Desde» y «Hasta», presiona «Generar» y luego «CSV»."],
      },
    ],
    quienEscribe: "Disponible para Coordinación y Auditor.",
  },
  {
    ruta: "/agenda",
    titulo: "Pacientes por citar",
    resumen:
      "Lista de trabajo de a quién falta citar con cada profesional. Las horas se agendan en SALUTEM; aquí se organiza y registra el contacto.",
    tareas: [
      {
        titulo: "Trabajar la lista del día",
        pasos: [
          "Elige el «Profesional» y el rango (por defecto «Dos semanas»).",
          "Parte por «Por citar»: está ordenada por prioridad y muestra un día sugerido con cupo.",
          "Llama al paciente y agenda la hora en SALUTEM.",
          "Presiona «Registrar contacto» y elige el resultado: «Agendada en SALUTEM», «No contesta», «Rechaza» u «Otro».",
        ],
      },
      {
        titulo: "Cargar la disponibilidad de un profesional",
        pasos: [
          "Abre «Disponibilidad semanal».",
          "Elige el día, indica el «Cupo diario» y presiona «Guardar día».",
        ],
      },
    ],
    etiquetas: [
      { texto: "Control vencido", tono: "destructive", significado: "La fecha del próximo control ya pasó." },
      { texto: "Control próximo", tono: "warning", significado: "El próximo control cae dentro del rango elegido." },
      { texto: "Seguimiento receta", tono: "info", significado: "Una receta se revisa en los próximos 30 días." },
      { texto: "En reposo hasta…", tono: "neutral", significado: "Tiene una licencia que cubre los días con cupo." },
      { texto: "Dijo agendada, sin hora en SALUTEM", tono: "warning", significado: "Se registró «Agendada en SALUTEM» hace más de 3 días hábiles y SALUTEM sigue sin la hora." },
    ],
    automatico:
      "Un paciente sale solo de la lista cuando SALUTEM tiene una hora vigente para él. Si registras «Agendada en SALUTEM», queda oculto 3 días hábiles mientras llega la hora.",
    consejos: ["Si todos aparecen «Sin cupo», el profesional no tiene disponibilidad cargada."],
  },
  {
    ruta: "/reportes",
    titulo: "Reportería",
    resumen: "Reportes operativos y de cumplimiento: operativo, convenio, carga laboral, licencias, ODAS vencidas y adherencia.",
    tareas: [
      {
        titulo: "Generar un reporte",
        pasos: [
          "Elige la pestaña del reporte.",
          "Completa los filtros marcados con * (por ejemplo «Desde» y «Hasta»).",
          "Presiona «Generar» o «Consultar».",
        ],
      },
    ],
    consejos: [
      "En «Adherencia» se cuentan las citas atendidas sobre las atendidas más inasistencias. Las anuladas y las futuras no cuentan.",
    ],
  },
  {
    ruta: "/lectura-pdf",
    titulo: "Lectura de PDF",
    resumen: "Sube un PDF para detectar sus campos y revisarlos contra un formulario.",
    tareas: [
      {
        titulo: "Leer un PDF",
        pasos: [
          "Presiona «Subir PDF».",
          "Revisa y corrige los «Campos detectados». Puedes agregar o quitar campos.",
          "Escribe el formulario destino y presiona «Confirmar».",
        ],
      },
    ],
    consejos: [
      "Se detectan las líneas con formato «Clave: Valor». Si el PDF es una imagen escaneada, completa los campos a mano.",
      "«Confirmar» valida los campos; no registra datos en la ficha del paciente.",
    ],
  },
  {
    ruta: "/usuarios",
    titulo: "Usuarios y roles",
    resumen: "Cuentas de acceso al SIGE y su perfil.",
    tareas: [
      {
        titulo: "Crear una cuenta",
        pasos: [
          "Presiona «Nuevo usuario».",
          "Completa usuario, nombre, rol y contraseña (mínimo 8 caracteres).",
          "Para quitar el acceso a alguien usa «Desactivar»; la cuenta no se borra.",
        ],
      },
    ],
    quienEscribe: "Solo Coordinación.",
  },
  {
    ruta: "/config-formularios",
    titulo: "Formularios dinámicos",
    resumen: "Definición de los campos configurables de un formulario.",
    tareas: [
      {
        titulo: "Modificar un formulario",
        pasos: [
          "Escribe la clave del formulario y presiona «Cargar».",
          "Presiona «Editar como nuevo borrador» y ajusta los campos.",
          "Presiona «Guardar borrador» y luego «Publicar borrador».",
        ],
      },
    ],
    consejos: ["Los campos con candado son de sistema y no se pueden quitar."],
    quienEscribe: "Solo Coordinación.",
  },
  {
    ruta: "/ventanas-proceso",
    titulo: "Ventanas de proceso",
    resumen: "Columnas visibles y orden por defecto de cada proceso.",
    tareas: [
      {
        titulo: "Crear una configuración",
        pasos: [
          "Elige el «Proceso».",
          "Escribe las columnas visibles separadas por coma y, si quieres, el orden por defecto.",
          "Presiona «Crear».",
        ],
      },
    ],
  },
  {
    ruta: "/profesionales",
    titulo: "Profesionales",
    resumen: "Catálogo de profesionales que se usa en Controles y en Pacientes por citar.",
    tareas: [
      {
        titulo: "Mantener el catálogo al día",
        pasos: [
          "Presiona «Importar desde SALUTEM» para traer los médicos nuevos.",
          "Usa «Nuevo profesional» para agregar a alguien a mano.",
          "Usa «Desactivar» para que alguien deje de aparecer en Pacientes por citar.",
        ],
      },
    ],
    consejos: [
      "Si cambias el nombre de un profesional que viene de SALUTEM, la próxima importación lo vuelve al nombre original.",
      "Haz clic en un profesional para ver su actividad: atenciones, controles y pacientes.",
    ],
  },
  {
    ruta: "/config-alertas",
    titulo: "Umbrales de alerta",
    resumen: "Con cuántos días de anticipación se avisa cada tipo de alerta, y los festivos que se descuentan.",
    tareas: [
      {
        titulo: "Ajustar un aviso",
        pasos: [
          "Cambia los «Días de anticipación» o marca si son días hábiles.",
          "Presiona «Guardar umbrales». El cambio se aplica en la próxima generación diaria (07:00).",
        ],
      },
      {
        titulo: "Agregar un festivo",
        pasos: ["En «Festivos», indica fecha y descripción y presiona «Agregar festivo»."],
      },
    ],
    consejos: ["Los festivos también se descuentan en Pacientes por citar."],
    quienEscribe: "Solo Coordinación.",
  },
];

export interface Pregunta {
  pregunta: string;
  respuesta: string;
  /** Guía relacionada, para el enlace «Ver guía». */
  guia?: string;
}

export const PREGUNTAS: Pregunta[] = [
  {
    pregunta: "Busco a un paciente y no aparece",
    respuesta:
      "Prueba con el RUT (con o sin puntos), con el folio exacto o con una parte del apellido. Si se atendió en SALUTEM pero nunca tuvo ingreso, búscalo en «Pendientes de folio».",
    guia: "/pendientes-folio",
  },
  {
    pregunta: "Registré algo en SALUTEM y no lo veo en el SIGE",
    respuesta:
      "La copia desde SALUTEM se actualiza cada pocos minutos: espera unos 5 minutos y recarga la página. Si después de una hora sigue sin aparecer, repórtalo.",
  },
  {
    pregunta: "¿Tengo que ingresar a mano los controles de SALUTEM?",
    respuesta:
      "No. Las atenciones médicas realizadas en SALUTEM crean su control solo, con la etiqueta SALUTEM. Ingresar el mismo control a mano lo duplica.",
    guia: "/controles",
  },
  {
    pregunta: "¿Por qué una licencia o receta de SALUTEM no quedó registrada?",
    respuesta:
      "Las licencias y recetas indicadas en SALUTEM llegan como sugerencia con una alerta. Una persona debe revisarlas y registrarlas; así se evitan errores de lectura.",
    guia: "/licencias",
  },
  {
    pregunta: "Un paciente ya tiene hora pero sigue en «Pacientes por citar»",
    respuesta:
      "Sale de la lista cuando la hora aparece en SALUTEM. Registra el contacto como «Agendada en SALUTEM»: lo oculta 3 días hábiles mientras la hora se sincroniza.",
    guia: "/agenda",
  },
  {
    pregunta: "¿Qué significan los números rojos del menú?",
    respuesta:
      "Son pendientes: en Licencias y Seguimiento EPT, alertas sin resolver; en Pendientes de folio, pacientes que esperan su registro. La campana del encabezado muestra las alertas sin leer.",
  },
  {
    pregunta: "No veo un botón que otra persona sí ve",
    respuesta:
      "Cada perfil tiene permisos distintos. El perfil Auditor solo consulta; en Seguimiento EPT solo Administrativo registra; corregir un folio es solo de Administrativo. Si necesitas otro perfil, pídelo a Coordinación.",
  },
  {
    pregunta: "¿El SIGE modifica datos en SALUTEM?",
    respuesta: "Nunca. La conexión es de solo lectura: el SIGE copia la información y la cruza con sus registros.",
  },
];

export interface Termino {
  termino: string;
  definicion: string;
}

export const GLOSARIO: Termino[] = [
  { termino: "SALUTEM", definicion: "Sistema de agenda y ficha clínica. El SIGE lee sus atenciones, citas y personas, sin modificarlas." },
  { termino: "ID SALUTEM", definicion: "Identificador de la persona en SALUTEM. Sirve para buscar pacientes sin RUT." },
  { termino: "Ingreso", definicion: "Episodio de atención de un paciente en el CEPA. Un paciente puede tener varios (reingresos)." },
  { termino: "Folio", definicion: "Identificador del ingreso, con formato F-2026-0001. Se asigna solo." },
  { termino: "Folio LM", definicion: "Número de la licencia médica. Es distinto del folio del ingreso." },
  { termino: "Falta folio", definicion: "Persona atendida en SALUTEM que aún no tiene ingreso en el SIGE." },
  { termino: "ODA", definicion: "Orden de atención asociada al ingreso, con fecha de vencimiento." },
  { termino: "ISL", definicion: "Instituto de Seguridad Laboral: recibe las licencias y los informes EPT." },
  { termino: "RECA", definicion: "Calificación del origen: enfermedad profesional (EP), enfermedad común (EC), accidente del trabajo (AT) o accidente común (AC)." },
  { termino: "GAF / EEAG", definicion: "Escala de funcionamiento global; se registra por tramo, por ejemplo 51-60." },
  { termino: "EPT", definicion: "Evaluación de Puesto de Trabajo." },
  { termino: "Extra sistema", definicion: "Licencia o fármaco indicado fuera del CEPA." },
  { termino: "Inasistencia", definicion: "Cita de SALUTEM a la que el paciente no llegó. Genera una alerta." },
  { termino: "Adherencia", definicion: "Citas atendidas sobre el total de atendidas más inasistencias." },
  { termino: "Cupo diario", definicion: "Pacientes que un profesional puede recibir cada día; ordena la lista de Pacientes por citar." },
  { termino: "Umbral", definicion: "Días de anticipación con que se genera una alerta." },
];

/** Accesos rápidos de la portada: las tareas más comunes. `roles` limita a quién se muestra. */
export interface Atajo {
  titulo: string;
  descripcion: string;
  guia: string;
  roles?: Rol[];
}

export const ATAJOS: Atajo[] = [
  { titulo: "Buscar un paciente", descripcion: "Por RUT, folio, nombre o ID SALUTEM", guia: "/ingresos" },
  { titulo: "Registrar una licencia", descripcion: "Desde una alerta o a mano", guia: "/licencias" },
  {
    titulo: "Completar un folio pendiente",
    descripcion: "Pacientes que llegan desde SALUTEM",
    guia: "/pendientes-folio",
    roles: ["Coordinacion", "Administrativo"],
  },
  { titulo: "Citar pacientes", descripcion: "La lista de trabajo por profesional", guia: "/agenda" },
];

/** Minúsculas y sin tildes, para buscar «farmacos» y encontrar «fármacos». */
export function normalizar(texto: string): string {
  return texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

/** Guía de la pantalla `pathname` (la ruta más larga que la contiene), para la ayuda contextual. */
export function guiaDeRuta(pathname: string): string | undefined {
  if (pathname === "/") return "/";
  return GUIAS.map((g) => g.ruta)
    .filter((r) => r !== "/" && (pathname === r || pathname.startsWith(`${r}/`)))
    .sort((a, b) => b.length - a.length)[0];
}

export function textoDeGuia(g: Guia): string {
  return normalizar(
    [
      g.titulo,
      g.resumen,
      g.automatico ?? "",
      g.quienEscribe ?? "",
      ...(g.consejos ?? []),
      ...g.tareas.flatMap((t) => [t.titulo, ...t.pasos]),
      ...(g.etiquetas ?? []).flatMap((e) => [e.texto, e.significado]),
    ].join(" "),
  );
}
