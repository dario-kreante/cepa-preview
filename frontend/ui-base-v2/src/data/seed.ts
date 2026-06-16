// Seed data for Sistema CEPA v2

export type AlertType = "danger" | "warn" | "info" | "success"

export interface Alert {
  id: string
  tipo: AlertType
  titulo: string
  paciente: string
  folio: string
  modulo: string
  hora: string
}

export interface Patient {
  folio: string
  nombre: string
  inicial: string
  rut: string
  region: string
  tipoDerivacion: string
  empresa: string
  fechaIngreso: string
  evaluacionMedica: "Realizada" | "Pendiente" | "En proceso"
  evaluacionPsicologica: "Realizada" | "Pendiente" | "En proceso"
  estado: "Activo" | "En tratamiento" | "Pendiente" | "Cerrado" | "Derivado"
  diagnostico: string
  edad: number
  genero: "F" | "M"
  telefono: string
  email: string
  profesionalRef: string
}

export interface Licencia {
  folio: string
  paciente: string
  tipoLicencia: string
  numero: string
  emision: string
  inicio: string
  fin: string
  dias: number
  estado: "Vigente" | "Finalizada" | "Rechazada"
  medico: string
}

export interface Receta {
  folio: string
  paciente: string
  farmaco: string
  dosis: string
  inicio: string
  vigenciaHasta: string
  medico: string
  estado: "Vigente" | "Por vencer" | "Vencida"
}

export interface Control {
  folio: string
  paciente: string
  tipo: string
  fecha: string
  hora: string
  profesional: string
  estado: "Agendado" | "Realizado" | "No asistió" | "Reagendado"
}

export const DASHBOARD_KPIS = {
  pacientesActivos: 186,
  ingresosMes: 12,
  licenciasActivas: 46,
  controlesEstaSemana: 58,
  recetasActivas: 112,
  eptEnProceso: 14,
  reintegrosProceso: 9,
  alertasCriticas: 3,
}

export const SERIE_ATENCIONES = [
  { mes: "Oct", atenciones: 142, inasistencias: 18 },
  { mes: "Nov", atenciones: 156, inasistencias: 22 },
  { mes: "Dic", atenciones: 138, inasistencias: 26 },
  { mes: "Ene", atenciones: 172, inasistencias: 20 },
  { mes: "Feb", atenciones: 184, inasistencias: 24 },
  { mes: "Mar", atenciones: 198, inasistencias: 19 },
  { mes: "Abr", atenciones: 156, inasistencias: 15 },
]

export const CARGA_PROFESIONAL = [
  { nombre: "Ps. Camila Díaz", atenciones: 42, color: "chart-1" },
  { nombre: "Ps. Rodrigo Fdez.", atenciones: 38, color: "chart-2" },
  { nombre: "Dr. Álvaro Soto", atenciones: 34, color: "chart-3" },
  { nombre: "Ps. Javiera Pinto", atenciones: 30, color: "chart-4" },
  { nombre: "Dra. Paulina Jara", atenciones: 28, color: "chart-5" },
  { nombre: "Ps. Andrés Meneses", atenciones: 24, color: "chart-1" },
]

export const DIAG_DISTRIBUTION = [
  { label: "Trastorno adaptativo mixto", valor: 28, pct: 22 },
  { label: "Episodio depresivo moderado", valor: 24, pct: 19 },
  { label: "Ansiedad generalizada", valor: 22, pct: 17 },
  { label: "Burnout laboral", valor: 18, pct: 14 },
  { label: "Estrés postraumático", valor: 14, pct: 11 },
  { label: "Otros", valor: 22, pct: 17 },
]

export const ALERTS: Alert[] = [
  { id: "a1", tipo: "danger", titulo: "Licencia vence mañana", paciente: "María Fernanda Sepúlveda Rojas", folio: "001", modulo: "Licencias", hora: "Hace 12 min" },
  { id: "a2", tipo: "danger", titulo: "Plazo ISL excedido", paciente: "Diego Ignacio Tapia Henríquez", folio: "004", modulo: "EPT", hora: "Hace 1 h" },
  { id: "a3", tipo: "danger", titulo: "Control crítico no agendado", paciente: "Álvaro Castro Lagos", folio: "016", modulo: "Controles", hora: "Hace 2 h" },
  { id: "a4", tipo: "warn", titulo: "Control médico en 3 días", paciente: "Javiera Espinoza Bravo", folio: "007", modulo: "Controles", hora: "Hace 2 h" },
  { id: "a5", tipo: "warn", titulo: "Receta próxima a vencer", paciente: "Camila Andrea Vergara Soto", folio: "003", modulo: "Fármacos", hora: "Hace 3 h" },
  { id: "a6", tipo: "warn", titulo: "Reevaluación EPT pendiente", paciente: "Tomás Figueroa Campos", folio: "022", modulo: "EPT", hora: "Ayer" },
  { id: "a7", tipo: "info", titulo: "Consentimiento informado pendiente", paciente: "Rodrigo Fuentes Gallardo", folio: "010", modulo: "Ingresos", hora: "Ayer" },
  { id: "a8", tipo: "info", titulo: "Control atrasado 2 días", paciente: "Matías Ortega Salinas", folio: "012", modulo: "Controles", hora: "Ayer" },
  { id: "a9", tipo: "success", titulo: "RECA recibida", paciente: "Antonia Pérez Silva", folio: "015", modulo: "Reintegro", hora: "Hoy 09:12" },
]

const NOMBRES: [string, string][] = [
  ["María Fernanda","Sepúlveda Rojas"],["Juan Pablo","Muñoz Fuentes"],["Camila Andrea","Vergara Soto"],
  ["Diego Ignacio","Tapia Henríquez"],["Francisca","Morales Díaz"],["Cristián","Núñez Parra"],
  ["Javiera","Espinoza Bravo"],["Sebastián","Riquelme Acuña"],["Valentina","Cortés Saavedra"],
  ["Rodrigo","Fuentes Gallardo"],["Catalina","Hernández Pino"],["Matías","Ortega Salinas"],
  ["Constanza","Vega Vidal"],["Felipe","Aravena Caro"],["Antonia","Pérez Silva"],
  ["Álvaro","Castro Lagos"],["Daniela","Soto Araya"],["Ignacio","Mella Inostroza"],
  ["Macarena","Rivas Pizarro"],["Cristóbal","Venegas Torres"],["Paola","Navarro Cáceres"],
  ["Tomás","Figueroa Campos"],["Isidora","Lagos Bustos"],["Nicolás","Reyes Contreras"],
  ["Bárbara","Urrutia Maturana"],
]

const DIAGNOSTICOS = [
  "Trastorno de adaptación mixto (F43.25)",
  "Episodio depresivo moderado (F32.1)",
  "Trastorno de ansiedad generalizada (F41.1)",
  "Trastorno por estrés postraumático (F43.1)",
  "Síndrome de Burnout laboral (Z73.0)",
  "Trastorno adaptativo con ansiedad (F43.22)",
  "Episodio depresivo leve (F32.0)",
  "Trastorno mixto ansioso-depresivo (F41.2)",
]

const REGIONES = ["RM","Maule","Valparaíso","Biobío","O'Higgins","Ñuble","Araucanía","Los Lagos","Coquimbo"]
const TIPOS_DERIVACION = ["ISL","Mutual de Seguridad","ACHS","IST","Espontánea","Convenio Educación","Convenio Salud"]
const EMPRESAS = [
  "Maderas del Maule SpA","Servicios Integrales RM Ltda.","Transportes Andino S.A.",
  "Colegio San Francisco","Hospital Regional de Talca","Constructora Llanura Ltda.",
  "Retail Cordillera SpA","ISL - Derivación directa","Municipalidad de Curicó","Viñas del Valle Ltda.",
]
const ESTADOS: Patient["estado"][] = ["Activo","En tratamiento","Pendiente","Cerrado","Derivado"]
const EVAL: Patient["evaluacionMedica"][] = ["Realizada","Pendiente","En proceso"]
const PROFESIONALES = [
  "Ps. Camila Díaz Torres","Ps. Rodrigo Fernández Ibáñez","Ps. Javiera Pinto Contador",
  "Dr. Álvaro Soto Farías","Dra. Paulina Jara Méndez",
]

function seeded(n: number) {
  let s = n
  return () => {
    s = (s * 9301 + 49297) % 233280
    return s / 233280
  }
}

export const PATIENTS: Patient[] = NOMBRES.map((nm, i) => {
  const rnd = seeded(i + 1)
  const folio = String(i + 1).padStart(3, "0")
  const rutN = 10000000 + Math.floor(rnd() * 20000000)
  const dv = (() => {
    let sum = 0, mul = 2
    const s = String(rutN)
    for (let j = s.length - 1; j >= 0; j--) {
      sum += parseInt(s[j]) * mul
      mul = mul === 7 ? 2 : mul + 1
    }
    const res = 11 - (sum % 11)
    if (res === 11) return "0"
    if (res === 10) return "K"
    return String(res)
  })()
  const rutStr = String(rutN).replace(/\B(?=(\d{3})+(?!\d))/g, ".")
  const fechaIng = `${String(Math.floor(rnd() * 28) + 1).padStart(2, "0")}-0${Math.floor(rnd() * 4) + 1}-2026`
  const estado = ESTADOS[Math.floor(rnd() * ESTADOS.length)]
  return {
    folio,
    nombre: `${nm[0]} ${nm[1]}`,
    inicial: `${nm[0][0]}${nm[1][0]}`,
    rut: `${rutStr}-${dv}`,
    region: REGIONES[Math.floor(rnd() * REGIONES.length)],
    tipoDerivacion: TIPOS_DERIVACION[Math.floor(rnd() * TIPOS_DERIVACION.length)],
    empresa: EMPRESAS[Math.floor(rnd() * EMPRESAS.length)],
    fechaIngreso: fechaIng,
    evaluacionMedica: EVAL[Math.floor(rnd() * EVAL.length)],
    evaluacionPsicologica: EVAL[Math.floor(rnd() * EVAL.length)],
    estado,
    diagnostico: DIAGNOSTICOS[Math.floor(rnd() * DIAGNOSTICOS.length)],
    edad: Math.floor(rnd() * 45) + 22,
    genero: rnd() > 0.5 ? "F" : "M",
    telefono: `+569 ${Math.floor(rnd() * 90000000) + 10000000}`,
    email: `${nm[0].toLowerCase().split(" ")[0]}.${nm[1].toLowerCase().split(" ")[0]}@correo.cl`,
    profesionalRef: PROFESIONALES[Math.floor(rnd() * PROFESIONALES.length)],
  }
})

export const LICENCIAS: Licencia[] = PATIENTS.slice(0, 15).map((p, i) => ({
  folio: p.folio,
  paciente: p.nombre,
  tipoLicencia: ["LM-3","LM-5","LM-6"][i % 3],
  numero: `LM-${10000 + i * 17}`,
  emision: `${String((i % 20) + 1).padStart(2, "0")}-03-2026`,
  inicio: `${String((i % 20) + 1).padStart(2, "0")}-03-2026`,
  fin: `${String((i % 15) + 10).padStart(2, "0")}-04-2026`,
  dias: [7, 14, 30, 15, 21][i % 5],
  estado: (["Vigente", "Vigente", "Finalizada", "Vigente", "Rechazada"] as const)[i % 5],
  medico: ["Dr. Álvaro Soto", "Dra. Paulina Jara", "Dr. Enrique Valdés"][i % 3],
}))

export const RECETAS: Receta[] = PATIENTS.slice(0, 18).map((p, i) => ({
  folio: p.folio,
  paciente: p.nombre,
  farmaco: ["Sertralina 50mg", "Fluoxetina 20mg", "Escitalopram 10mg", "Venlafaxina 75mg", "Clonazepam 0.5mg", "Trazodona 50mg"][i % 6],
  dosis: ["1 comp. mañana", "1 comp. c/12h", "2 comp. noche", "1 comp. mañana"][i % 4],
  inicio: `${String((i % 25) + 1).padStart(2, "0")}-03-2026`,
  vigenciaHasta: `${String((i % 25) + 1).padStart(2, "0")}-05-2026`,
  medico: ["Dr. Álvaro Soto", "Dra. Paulina Jara", "Dr. Enrique Valdés"][i % 3],
  estado: (["Vigente", "Vigente", "Por vencer", "Vigente", "Vencida"] as const)[i % 5],
}))

export const CONTROLES: Control[] = PATIENTS.slice(0, 20).map((p, i) => ({
  folio: p.folio,
  paciente: p.nombre,
  tipo: ["Control médico", "Sesión psicológica", "Control EPT", "Reevaluación"][i % 4],
  fecha: `${String((i % 28) + 1).padStart(2, "0")}-04-2026`,
  hora: `${String(9 + (i % 8)).padStart(2, "0")}:${i % 2 === 0 ? "00" : "30"}`,
  profesional: PROFESIONALES[i % PROFESIONALES.length],
  estado: (["Agendado", "Realizado", "No asistió", "Reagendado", "Agendado"] as const)[i % 5],
}))

// EPT (Evaluación Puesto de Trabajo)
export interface EPT {
  folio: string
  numero: string
  paciente: string
  rut: string
  razonSocial: string
  unidad: string
  cargo: string
  tipoEvaluacion: "EM" | "EPS" | "EM+EPS"
  eptista: string
  factorRiesgo: string
  nEntrevistas: number
  testigos: boolean
  cantidadTestigos: number
  plazoInformeEPT: number
  plazoPortalISL: number
  estadoEnvio: "Enviado" | "Pendiente" | "En revisión"
  estadoCaso: "Activo" | "En tratamiento" | "Pendiente" | "Cerrado"
}

const EPTISTAS = ["Ps. Lorena Baeza", "Ps. Tomás Jiménez", "Ps. Sofía Retamal"]
const FACTORES = [
  "Violencia laboral", "Carga mental alta", "Hostigamiento", "Acoso sexual",
  "Sobrecarga horaria", "Conflicto de rol", "Violencia verbal",
]
const CARGOS = [
  "Operario turno", "Administrativo", "Supervisor", "Jefe de sección",
  "Asistente", "Técnico", "Docente", "Auxiliar",
]

export const EPTS: EPT[] = PATIENTS.slice(0, 14).map((p, i) => {
  const tipo = (["EM", "EPS", "EM+EPS"] as const)[i % 3]
  return {
    folio: p.folio,
    numero: `EPT-2026-${String(100 + i).padStart(4, "0")}`,
    paciente: p.nombre,
    rut: p.rut,
    razonSocial: p.empresa,
    unidad: ["Planta Talca", "Oficina Central", "Sucursal Norte", "Operaciones Sur"][i % 4],
    cargo: CARGOS[i % CARGOS.length],
    tipoEvaluacion: tipo,
    eptista: EPTISTAS[i % EPTISTAS.length],
    factorRiesgo: FACTORES[i % FACTORES.length],
    nEntrevistas: 2 + (i % 4),
    testigos: i % 3 === 0,
    cantidadTestigos: i % 3 === 0 ? 2 + (i % 3) : 0,
    plazoInformeEPT: 10 + (i % 12),
    plazoPortalISL: 15 + (i % 18),
    estadoEnvio: (["Enviado", "Pendiente", "En revisión", "Enviado"] as const)[i % 4],
    estadoCaso: (["Activo", "En tratamiento", "Pendiente", "Cerrado"] as const)[i % 4],
  }
})

// Reintegros
export interface Reintegro {
  folio: string
  paciente: string
  tipoDerivacion: string
  numeroRECA: string
  fechaRECA: string
  tipoRECA: "EP" | "EC"
  riesgosCalificados: string
  medidasCorrectivas: "Implementadas" | "Pendientes" | "Parciales"
  verificacion: "Verificada" | "Pendiente" | "En proceso"
  estadoReintegro: "En proceso" | "Reintegrado" | "Pendiente"
  fechaReintegro: string
  tipoAlta: string
}

export const REINTEGROS: Reintegro[] = PATIENTS.slice(0, 12).map((p, i) => ({
  folio: p.folio,
  paciente: p.nombre,
  tipoDerivacion: p.tipoDerivacion,
  numeroRECA: `RECA-${String(20000 + i * 23).slice(-5)}`,
  fechaRECA: `${String((i % 28) + 1).padStart(2, "0")}-0${(i % 3) + 1}-2026`,
  tipoRECA: (["EP", "EC"] as const)[i % 2],
  riesgosCalificados: ["Psicosocial alto", "Psicosocial medio", "Ergonómico", "Organizacional"][i % 4],
  medidasCorrectivas: (["Implementadas", "Pendientes", "Parciales"] as const)[i % 3],
  verificacion: (["Verificada", "Pendiente", "En proceso"] as const)[i % 3],
  estadoReintegro: (["En proceso", "Reintegrado", "Pendiente"] as const)[i % 3],
  fechaReintegro: `${String((i % 28) + 1).padStart(2, "0")}-04-2026`,
  tipoAlta: ["Alta terapéutica", "Alta médica", "Alta psicológica", "Derivación"][i % 4],
}))

// Agenda slots
export interface AgendaSlot {
  profesional: string
  hora: string
  paciente: string
  tipo: string
  estado: "Confirmada" | "En espera" | "Reagendada"
}

export const AGENDA_PROFESIONALES = [
  { key: "camila",  nombre: "Ps. Camila Díaz",     color: "oklch(0.56 0.14 180)" },
  { key: "rodrigo", nombre: "Ps. Rodrigo Fdez.",   color: "oklch(0.56 0.16 230)" },
  { key: "alvaro",  nombre: "Dr. Álvaro Soto",     color: "oklch(0.60 0.16 25)" },
  { key: "javiera", nombre: "Ps. Javiera Pinto",   color: "oklch(0.58 0.18 290)" },
  { key: "paulina", nombre: "Dra. Paulina Jara",   color: "oklch(0.62 0.14 85)" },
  { key: "andres",  nombre: "Ps. Andrés Meneses",  color: "oklch(0.60 0.14 155)" },
]

const SLOTS_SEED: Array<[string, string, number, string, AgendaSlot["estado"]]> = [
  ["camila", "08:30", 0, "Sesión psicológica", "Confirmada"],
  ["camila", "09:30", 3, "Control psi.", "Confirmada"],
  ["camila", "10:30", 5, "Primera consulta", "En espera"],
  ["camila", "14:30", 8, "Sesión psicológica", "Confirmada"],
  ["camila", "17:30", 12, "Evaluación EPT", "Confirmada"],
  ["rodrigo", "09:30", 2, "Sesión psicológica", "Confirmada"],
  ["rodrigo", "10:30", 7, "Reevaluación", "Confirmada"],
  ["rodrigo", "11:30", 10, "Sesión psicológica", "En espera"],
  ["rodrigo", "15:30", 14, "Control psi.", "Reagendada"],
  ["alvaro", "08:30", 1, "Control médico", "Confirmada"],
  ["alvaro", "09:30", 4, "Control médico", "Confirmada"],
  ["alvaro", "11:30", 9, "Control médico", "Confirmada"],
  ["alvaro", "16:30", 11, "Control médico", "En espera"],
  ["javiera", "10:30", 6, "Sesión psicológica", "Confirmada"],
  ["javiera", "12:30", 13, "Primera consulta", "En espera"],
  ["javiera", "15:30", 18, "Sesión psicológica", "Confirmada"],
  ["paulina", "09:30", 15, "Control médico", "Confirmada"],
  ["paulina", "14:30", 19, "Control médico", "Confirmada"],
  ["paulina", "16:30", 20, "Reevaluación", "Confirmada"],
  ["andres", "08:30", 16, "Primera consulta", "En espera"],
  ["andres", "11:30", 17, "Sesión psicológica", "Confirmada"],
  ["andres", "15:30", 21, "Evaluación EPT", "Confirmada"],
  ["andres", "17:30", 22, "Sesión psicológica", "Confirmada"],
]

export const AGENDA_SLOTS: AgendaSlot[] = SLOTS_SEED.map(([prof, hora, pi, tipo, estado]) => ({
  profesional: prof,
  hora,
  paciente: PATIENTS[pi]?.nombre ?? "Paciente",
  tipo,
  estado,
}))

// Reportería — series mensuales
export const SERIE_INGRESOS = [
  { mes: "Nov 25", value: 8 },
  { mes: "Dic 25", value: 10 },
  { mes: "Ene 26", value: 14 },
  { mes: "Feb 26", value: 11 },
  { mes: "Mar 26", value: 16 },
  { mes: "Abr 26", value: 12 },
]

export const TIPOS_DERIVACION_SEED = TIPOS_DERIVACION

// Auditoría por paciente
export interface AuditRow {
  folio: string
  paciente: string
  rut: string
  mes: string
  fechaIngreso: string
  diep: "Sí" | "No"
  acogida: "Realizada" | "Pendiente"
  evalMed: "Realizada" | "Pendiente" | "En proceso"
  evalPsi: "Realizada" | "Pendiente" | "En proceso"
  plazoInforme: number
  obstaculizacion: boolean
  envioInforme: "Enviado" | "Pendiente"
  recaTipo: "EP" | "EC"
  recaNumero: string
  estado: Patient["estado"]
  tipoAlta: string
  encuestaSatisfaccion: "Respondida" | "Pendiente" | "No aplica"
}

const MESES = ["Enero", "Febrero", "Marzo", "Abril"]

export const AUDIT_ROWS: AuditRow[] = PATIENTS.map((p, i) => ({
  folio: p.folio,
  paciente: p.nombre,
  rut: p.rut,
  mes: MESES[i % 4],
  fechaIngreso: p.fechaIngreso,
  diep: (["Sí", "Sí", "No"] as const)[i % 3],
  acogida: (["Realizada", "Pendiente", "Realizada"] as const)[i % 3],
  evalMed: p.evaluacionMedica,
  evalPsi: p.evaluacionPsicologica,
  plazoInforme: 15 + (i % 20),
  obstaculizacion: i % 7 === 0,
  envioInforme: (i % 3 === 0 ? "Pendiente" : "Enviado"),
  recaTipo: (["EP", "EC"] as const)[i % 2],
  recaNumero: `RECA-${String(20000 + i * 7).slice(-5)}`,
  estado: p.estado,
  tipoAlta: ["Alta terapéutica", "Alta médica", "Alta psicológica", "Derivación", "Abandono"][i % 5],
  encuestaSatisfaccion: (["Respondida", "Pendiente", "No aplica", "Respondida"] as const)[i % 4],
}))
