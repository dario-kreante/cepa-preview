/* =========================================================
   Datos semilla - Sistema CEPA
   25 pacientes con RUTs chilenos válidos y datos cruzados
   ========================================================= */

// RUT generator: recibe cuerpo, calcula dígito verificador
function calcDV(rutNumber) {
  let sum = 0, mul = 2;
  const s = String(rutNumber);
  for (let i = s.length - 1; i >= 0; i--) {
    sum += parseInt(s[i]) * mul;
    mul = mul === 7 ? 2 : mul + 1;
  }
  const res = 11 - (sum % 11);
  if (res === 11) return '0';
  if (res === 10) return 'K';
  return String(res);
}
function fmtRut(n) {
  const dv = calcDV(n);
  const s = String(n);
  const rev = s.split('').reverse().join('');
  const grouped = rev.match(/.{1,3}/g).join('.').split('').reverse().join('');
  return `${grouped}-${dv}`;
}

const REGIONES = ['RM','Maule','Valparaíso','Biobío','O\'Higgins','Ñuble','Araucanía','Los Lagos','Coquimbo'];
const COMUNAS_MAULE = ['Talca','Curicó','Linares','Constitución','San Javier','Cauquenes','Molina'];

const NOMBRES = [
  ['María Fernanda','Sepúlveda Rojas'],['Juan Pablo','Muñoz Fuentes'],['Camila Andrea','Vergara Soto'],
  ['Diego Ignacio','Tapia Henríquez'],['Francisca','Morales Díaz'],['Cristián','Núñez Parra'],
  ['Javiera','Espinoza Bravo'],['Sebastián','Riquelme Acuña'],['Valentina','Cortés Saavedra'],
  ['Rodrigo','Fuentes Gallardo'],['Catalina','Hernández Pino'],['Matías','Ortega Salinas'],
  ['Constanza','Vega Vidal'],['Felipe','Aravena Caro'],['Antonia','Pérez Silva'],
  ['Álvaro','Castro Lagos'],['Daniela','Soto Araya'],['Ignacio','Mella Inostroza'],
  ['Macarena','Rivas Pizarro'],['Cristóbal','Venegas Torres'],['Paola','Navarro Cáceres'],
  ['Tomás','Figueroa Campos'],['Isidora','Lagos Bustos'],['Nicolás','Reyes Contreras'],
  ['Bárbara','Urrutia Maturana']
];

const MEDICOS = [
  'Dr. Álvaro Soto Farías','Dra. Paulina Jara Méndez','Dr. Enrique Valdés Rojas',
  'Dra. Carla Vidal Herrera','Dr. Manuel Leiva Ortiz'
];
const PSICOLOGOS = [
  'Ps. Camila Díaz Torres','Ps. Rodrigo Fernández Ibáñez','Ps. Javiera Pinto Contador',
  'Ps. Andrés Meneses Rivera','Ps. Pilar Contreras Zamora','Ps. Marcos Soto Vega'
];
const EPTISTAS = ['Ps. Lorena Baeza Pardo','Ps. Tomás Jiménez Ñancupil','Ps. Sofía Retamal Leal'];

const EMPRESAS = [
  {razon: 'Maderas del Maule SpA', unidad: 'Planta Talca'},
  {razon: 'Servicios Integrales RM Ltda.', unidad: 'Oficina Central'},
  {razon: 'Transportes Andino S.A.', unidad: 'Operaciones Sur'},
  {razon: 'Colegio San Francisco', unidad: 'Administración'},
  {razon: 'Hospital Regional de Talca', unidad: 'Enfermería'},
  {razon: 'Constructora Llanura Ltda.', unidad: 'Obra Los Pinos'},
  {razon: 'Retail Cordillera SpA', unidad: 'Sucursal Mall Plaza'},
  {razon: 'ISL - Derivación directa', unidad: '-'},
  {razon: 'Municipalidad de Curicó', unidad: 'Dir. de Obras'},
  {razon: 'Viñas del Valle Ltda.', unidad: 'Bodegas'},
];

const DIAGNOSTICOS = [
  'Trastorno de adaptación mixto (F43.25)',
  'Episodio depresivo moderado (F32.1)',
  'Trastorno de ansiedad generalizada (F41.1)',
  'Trastorno por estrés postraumático (F43.1)',
  'Síndrome de Burnout laboral (Z73.0)',
  'Trastorno adaptativo con ansiedad (F43.22)',
  'Episodio depresivo leve (F32.0)',
  'Trastorno mixto ansioso-depresivo (F41.2)',
];

const TIPOS_DERIVACION = ['ISL','Mutual de Seguridad','ACHS','IST','Espontánea','Convenio Educación','Convenio Salud'];
const ESTADOS = ['Activo','En tratamiento','Pendiente','Cerrado','Derivado'];
const TIPOS_ALTA = ['Alta terapéutica','Alta médica','Alta psicológica','Abandono','Derivación'];

function seededRand(seed) {
  let s = seed;
  return () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };
}
const rnd = seededRand(42);
const pick = arr => arr[Math.floor(rnd() * arr.length)];
const pickInt = (a,b) => a + Math.floor(rnd()*(b-a+1));

// date helpers
function isoDate(y,m,d) { return new Date(y, m-1, d); }
function fmtDate(d) {
  if (!d) return '-';
  const dd = String(d.getDate()).padStart(2,'0');
  const mm = String(d.getMonth()+1).padStart(2,'0');
  return `${dd}-${mm}-${d.getFullYear()}`;
}
function addDays(d, n) { const r = new Date(d); r.setDate(r.getDate()+n); return r; }
function diffDays(a, b) { return Math.round((b - a) / (1000*60*60*24)); }

// === Build patients ===
const PATIENTS = NOMBRES.map((nombre, i) => {
  const folio = String(1 + i).padStart(3,'0');
  const rutNum = 11000000 + Math.floor(rnd() * 12000000);
  const empresa = pick(EMPRESAS);
  const estado = i < 18 ? pick(['Activo','En tratamiento','Pendiente']) : pick(['Cerrado','Derivado']);
  const ingresoMes = pickInt(1, 4); // ene-abr 2026
  const ingresoDia = pickInt(1, 28);
  const fechaIngreso = isoDate(2026, ingresoMes, ingresoDia);
  const fechaDIEP = addDays(fechaIngreso, pickInt(1, 3));
  const fechaAcogida = addDays(fechaIngreso, pickInt(3, 7));
  const tieneEval = rnd() > 0.2;
  const medico = pick(MEDICOS);
  const psicologo = pick(PSICOLOGOS);
  const eptista = pick(EPTISTAS);
  const dx = pick(DIAGNOSTICOS);
  const region = pick(REGIONES);
  const comuna = region === 'Maule' ? pick(COMUNAS_MAULE) : region;
  const telefono = `+569 ${pickInt(4000,9999)} ${pickInt(1000,9999)}`;
  const correo = nombre[0].toLowerCase().replace(/\s/g,'.').normalize('NFD').replace(/[\u0300-\u036f]/g,'') + '@gmail.com';
  const tipoDeriv = pick(TIPOS_DERIVACION);
  const diasLicenciaTotal = pickInt(0, 95);
  const nSesiones = pickInt(0, 14);
  const proxControl = addDays(fechaIngreso, pickInt(20, 60));

  return {
    folio,
    rut: fmtRut(rutNum),
    rutNum,
    nombre: nombre[0] + ' ' + nombre[1],
    nombres: nombre[0],
    apellidos: nombre[1],
    inicial: nombre[0][0] + nombre[1][0],
    region,
    comuna,
    telefono,
    correo,
    tipoDerivacion: tipoDeriv,
    empresa: empresa.razon,
    unidadEmpresa: empresa.unidad,
    cargo: pick(['Operario','Administrativo','Supervisor','Docente','Profesional','Técnico','Jefatura']),
    mes: ['Ene','Feb','Mar','Abr'][ingresoMes-1],
    fechaIngreso,
    fechaDIEP,
    fechaAcogida,
    evaluacionMedica: tieneEval ? 'Realizada' : 'Pendiente',
    evaluacionPsicologica: rnd() > 0.25 ? 'Realizada' : 'Pendiente',
    medico,
    psicologo,
    eptista,
    diagnostico: dx,
    estado,
    obstaculizacion: rnd() > 0.85,
    plazoInformeDias: pickInt(15, 30),
    envioInforme: rnd() > 0.4 ? 'Enviado' : 'Pendiente',
    recaTipo: rnd() > 0.5 ? 'EP' : 'EC',
    recaNumero: `RECA-${pickInt(1000,9999)}`,
    tipoAlta: estado === 'Cerrado' ? pick(TIPOS_ALTA) : '-',
    revisionCaso: rnd() > 0.7 ? 'OK' : 'Pendiente',
    encuestaSatisfaccion: estado === 'Cerrado' && rnd() > 0.3 ? 'Respondida' : 'Pendiente',
    diasLicenciaTotal,
    nSesionesMedicas: Math.floor(nSesiones / 2),
    nSesionesPsicologicas: nSesiones,
    proxControl,
    observaciones: ''
  };
});

// === Build licencias ===
const LICENCIAS = [];
let licId = 1;
PATIENTS.forEach(p => {
  const nLic = pickInt(0, 4);
  let cursor = p.fechaIngreso;
  for (let j = 0; j < nLic; j++) {
    const dias = pick([7, 10, 14, 15, 21, 28, 30]);
    const inicio = addDays(cursor, pickInt(0, 10));
    const termino = addDays(inicio, dias-1);
    cursor = addDays(termino, pickInt(1, 5));
    LICENCIAS.push({
      id: licId++,
      folio: p.folio,
      paciente: p.nombre,
      rut: p.rut,
      region: p.region,
      folioLM: `LM-${String(10000 + licId).padStart(5,'0')}`,
      dias,
      fechaInicio: inicio,
      fechaTermino: termino,
      tipoReposo: pick(['Total','Parcial']),
      tipoLicencia: pick(['1','5','6']),
      envioISL: rnd() > 0.25 ? 'Enviado' : 'Pendiente',
      fechaEmision: addDays(inicio, -1),
      eeag: pickInt(50, 75),
      observaciones: ''
    });
  }
});

// === Build farmacos ===
const FARMACOS_CATALOGO = [
  {nombre: 'Sertralina', dosis: '50mg', frecuencia: '1/día'},
  {nombre: 'Fluoxetina', dosis: '20mg', frecuencia: '1/día'},
  {nombre: 'Escitalopram', dosis: '10mg', frecuencia: '1/día'},
  {nombre: 'Venlafaxina', dosis: '75mg', frecuencia: '1/día'},
  {nombre: 'Quetiapina', dosis: '25mg', frecuencia: 'Noche'},
  {nombre: 'Clonazepam', dosis: '0.5mg', frecuencia: '2/día'},
  {nombre: 'Mirtazapina', dosis: '30mg', frecuencia: 'Noche'},
];

const RECETAS = [];
let recId = 1;
PATIENTS.forEach(p => {
  if (rnd() > 0.3) {
    const f = pick(FARMACOS_CATALOGO);
    const emision = addDays(p.fechaIngreso, pickInt(5, 15));
    RECETAS.push({
      id: recId++,
      folio: p.folio,
      paciente: p.nombre,
      rut: p.rut,
      medico: p.medico,
      medicamento: f.nombre,
      dosis: f.dosis,
      frecuencia: f.frecuencia,
      marca: pick(['Genérico','Lab. Chile','Saval','Andrómaco']),
      fechaEmision: emision,
      fechaRevision: addDays(emision, 30),
      fechaEnvioAhumada: addDays(emision, 1),
      gestionSocorro1: rnd() > 0.5 ? addDays(emision, 3) : null,
      gestionSocorro2: rnd() > 0.7 ? addDays(emision, 10) : null,
      gestionSocorro3: null,
      disminucion: rnd() > 0.8,
      cambioEsquema: rnd() > 0.85,
      estado: rnd() > 0.2 ? 'Activa' : 'Suspendida',
      observaciones: ''
    });
  }
});

// === Controles médicos ===
const CONTROLES = PATIENTS.map(p => ({
  folio: p.folio,
  paciente: p.nombre,
  rut: p.rut,
  region: p.region,
  medico: p.medico,
  fechaIngreso: p.fechaIngreso,
  semanaControl: Math.max(1, Math.ceil(diffDays(p.fechaIngreso, p.proxControl) / 7)),
  proxControl: p.proxControl,
  agendado: rnd() > 0.3,
  licenciaActiva: LICENCIAS.find(l => l.folio === p.folio && l.fechaTermino >= new Date(2026, 3, 18)),
  diasLicencia: p.diasLicenciaTotal,
  tipoReposo: pick(['Total','Parcial','-']),
  tipoLicencia: pick(['1','5','6','-']),
  gaf: pickInt(45, 80),
  recaEstado: pick(['Recibida','Pendiente','En revisión']),
  fechaRecepcionRECA: rnd() > 0.5 ? addDays(p.fechaIngreso, pickInt(10, 40)) : null,
  fechaPostRECA: rnd() > 0.6 ? addDays(p.fechaIngreso, pickInt(45, 90)) : null,
}));

// === EPT ===
const EPTS = PATIENTS.slice(0, 14).map((p, i) => ({
  folio: p.folio,
  numero: `EPT-${String(1001 + i).padStart(4,'0')}`,
  mes: p.mes,
  fechaIngreso: p.fechaIngreso,
  fechaEntregaISL: addDays(p.fechaIngreso, pickInt(30, 60)),
  paciente: p.nombre,
  rut: p.rut,
  region: p.region,
  eptista: p.eptista,
  tipoEvaluacion: pick(['EM','EPS','EM+EPS']),
  factorRiesgo: pick(['Sobrecarga laboral','Acoso laboral','Violencia en el trabajo','Carga mental excesiva','Conflictos interpersonales','Ritmo de trabajo acelerado']),
  razonSocial: p.empresa,
  unidad: p.unidadEmpresa,
  cargo: p.cargo,
  horario: pick(['Diurno 08:00-17:30','Turnos 12x12','Nocturno 20:00-06:00','Part-time']),
  correoEmpleador1: 'rrhh@' + p.empresa.toLowerCase().replace(/[^a-z]/g,'').slice(0,10) + '.cl',
  correoEmpleador2: 'coordinacion@' + p.empresa.toLowerCase().replace(/[^a-z]/g,'').slice(0,10) + '.cl',
  plazoEvidencia: pickInt(5, 15),
  plazoInsumos: pickInt(10, 20),
  testigos: rnd() > 0.4,
  cantidadTestigos: pickInt(0, 3),
  nEntrevistas: pickInt(1, 6),
  plazoInformeEPT: pickInt(15, 30),
  plazoPortalISL: pickInt(20, 40),
  estadoEnvio: pick(['Enviado','Pendiente','En preparación']),
  estadoCaso: p.estado,
}));

// === Reintegro ===
const REINTEGROS = PATIENTS.slice(5, 20).map((p, i) => ({
  folio: p.folio,
  tipoDerivacion: p.tipoDerivacion,
  fecha: p.fechaIngreso,
  paciente: p.nombre,
  rut: p.rut,
  region: p.region,
  solicitudRECA: pick(['Solicitada','Pendiente']),
  fechaSolicitudRECA: addDays(p.fechaIngreso, pickInt(5, 15)),
  fechaRECA: addDays(p.fechaIngreso, pickInt(30, 60)),
  tipoRECA: p.recaTipo,
  numeroRECA: p.recaNumero,
  medidasCorrectivas: pick(['Implementadas','Parciales','Pendientes','No aplica']),
  verificacion: pick(['Verificada','Pendiente','En proceso']),
  riesgosCalificados: pick(['Psicosocial','Ergonómico','Psicosocial + Ergonómico','Ninguno']),
  razonSocial: p.empresa,
  estadoReintegro: pick(['Reintegrado','En proceso','Pendiente','No aplica']),
  fechaReintegro: rnd() > 0.5 ? addDays(p.fechaIngreso, pickInt(60, 120)) : null,
  remitidoISL: rnd() > 0.4,
  estadoCaso: p.estado,
  tipoAlta: p.tipoAlta,
  altaMedica: rnd() > 0.5 ? addDays(p.fechaIngreso, pickInt(90, 150)) : null,
  altaPsicologica: rnd() > 0.5 ? addDays(p.fechaIngreso, pickInt(90, 150)) : null,
}));

// === Alertas del día ===
const today = new Date(2026, 3, 18); // 18-abr-2026
const ALERTS = [
  { id: 1, tipo: 'danger',  titulo: 'Licencia vence mañana',        paciente: PATIENTS[0].nombre,  folio: PATIENTS[0].folio,  hora: 'Hace 12 min', modulo: 'Licencias',    desc: 'LM-10003 · 14 días · Vence 19-04-2026' },
  { id: 2, tipo: 'danger',  titulo: 'Plazo ISL excedido',           paciente: PATIENTS[3].nombre,  folio: PATIENTS[3].folio,  hora: 'Hace 1 h',    modulo: 'EPT',          desc: 'EPT-1004 · Entrega ISL 15-04-2026' },
  { id: 3, tipo: 'warn',    titulo: 'Control médico en 3 días',     paciente: PATIENTS[6].nombre,  folio: PATIENTS[6].folio,  hora: 'Hace 2 h',    modulo: 'Controles',    desc: 'Próximo control: 21-04-2026 · Dr. Valdés' },
  { id: 4, tipo: 'warn',    titulo: 'Receta próxima a vencer',      paciente: PATIENTS[2].nombre,  folio: PATIENTS[2].folio,  hora: 'Hace 3 h',    modulo: 'Fármacos',     desc: 'Sertralina 50mg · Vence en 5 días' },
  { id: 5, tipo: 'info',    titulo: 'Consentimiento informado pendiente', paciente: PATIENTS[9].nombre, folio: PATIENTS[9].folio, hora: 'Ayer', modulo: 'Ingresos', desc: 'Primera acogida sin firma registrada' },
  { id: 6, tipo: 'warn',    titulo: 'Control atrasado 2 días',      paciente: PATIENTS[11].nombre, folio: PATIENTS[11].folio, hora: 'Ayer',        modulo: 'Controles',    desc: 'Debió realizarse el 16-04-2026' },
  { id: 7, tipo: 'success', titulo: 'RECA recibida',                paciente: PATIENTS[14].nombre, folio: PATIENTS[14].folio, hora: 'Hoy 09:12',   modulo: 'Reintegro',    desc: `${PATIENTS[14].recaNumero} · Tipo ${PATIENTS[14].recaTipo}` },
  { id: 8, tipo: 'info',    titulo: 'Nueva licencia registrada',    paciente: PATIENTS[5].nombre,  folio: PATIENTS[5].folio,  hora: 'Hoy 10:45',   modulo: 'Licencias',    desc: 'LM tipo 5 · 21 días · Psiquiátrica' },
  { id: 9, tipo: 'danger',  titulo: 'Informe EPT vence hoy',        paciente: PATIENTS[7].nombre,  folio: PATIENTS[7].folio,  hora: 'Hoy',         modulo: 'EPT',          desc: 'Plazo informe EPT 30 días cumplido' },
  { id:10, tipo: 'warn',    titulo: 'Receta pendiente de envío',    paciente: PATIENTS[13].nombre, folio: PATIENTS[13].folio, hora: 'Hace 5 h',    modulo: 'Fármacos',     desc: 'Emitida hace 2 días sin gestión' },
];

// === KPIs dashboard (snapshot 18-abr-2026) ===
const DASHBOARD_KPIS = {
  pacientesActivos: PATIENTS.filter(p => p.estado !== 'Cerrado' && p.estado !== 'Derivado').length,
  ingresosMes: PATIENTS.filter(p => p.mes === 'Abr').length,
  licenciasActivas: LICENCIAS.filter(l => l.fechaTermino >= today).length,
  diasLicenciaPromedio: Math.round(LICENCIAS.reduce((s,l) => s+l.dias, 0) / Math.max(1, LICENCIAS.length)),
  recetasActivas: RECETAS.filter(r => r.estado === 'Activa').length,
  controlesEstaSemana: CONTROLES.filter(c => {
    const d = diffDays(today, c.proxControl);
    return d >= 0 && d <= 7;
  }).length,
  eptEnProceso: EPTS.filter(e => e.estadoCaso !== 'Cerrado').length,
  reintegrosProceso: REINTEGROS.filter(r => r.estadoReintegro === 'En proceso').length,
  altasMes: PATIENTS.filter(p => p.estado === 'Cerrado').length,
  alertasCriticas: ALERTS.filter(a => a.tipo === 'danger').length,
};

// === Reportería - inasistencias y series ===
const SERIE_INGRESOS = [
  { mes: 'Oct 25', value: 17 }, { mes: 'Nov 25', value: 22 },
  { mes: 'Dic 25', value: 15 }, { mes: 'Ene 26', value: 24 },
  { mes: 'Feb 26', value: 28 }, { mes: 'Mar 26', value: 31 },
  { mes: 'Abr 26', value: 19 },
];
const SERIE_ATENCIONES = [
  { mes: 'Oct 25', atenciones: 186, inasistencias: 23 },
  { mes: 'Nov 25', atenciones: 204, inasistencias: 28 },
  { mes: 'Dic 25', atenciones: 152, inasistencias: 19 },
  { mes: 'Ene 26', atenciones: 231, inasistencias: 31 },
  { mes: 'Feb 26', atenciones: 247, inasistencias: 34 },
  { mes: 'Mar 26', atenciones: 268, inasistencias: 27 },
  { mes: 'Abr 26', atenciones: 162, inasistencias: 18 },
];
const CARGA_PROFESIONAL = [
  {nombre: 'Dr. Álvaro Soto', casos: 18, atenciones: 54, disponibilidad: 72},
  {nombre: 'Dra. Paulina Jara', casos: 14, atenciones: 47, disponibilidad: 58},
  {nombre: 'Ps. Camila Díaz', casos: 22, atenciones: 66, disponibilidad: 88},
  {nombre: 'Ps. Rodrigo Fernández', casos: 19, atenciones: 58, disponibilidad: 76},
  {nombre: 'Ps. Javiera Pinto', casos: 16, atenciones: 48, disponibilidad: 64},
  {nombre: 'Dr. Enrique Valdés', casos: 12, atenciones: 38, disponibilidad: 48},
];

// === Agendamiento ===
const AGENDA_SLOTS = (() => {
  const slots = [];
  const horas = ['08:30','09:30','10:30','11:30','12:30','14:30','15:30','16:30','17:30'];
  const profesionales = [
    {nombre:'Dr. Álvaro Soto',     color:'#2f6ea4', key:'medico1'},
    {nombre:'Dra. Paulina Jara',   color:'#0e9384', key:'medico2'},
    {nombre:'Ps. Camila Díaz',     color:'#7a5af8', key:'psi1'},
    {nombre:'Ps. Rodrigo Fernández', color:'#d97706', key:'psi2'},
    {nombre:'Ps. Javiera Pinto',   color:'#b42318', key:'psi3'},
    {nombre:'Dr. Enrique Valdés',  color:'#1570ef', key:'medico3'},
  ];
  profesionales.forEach(prof => {
    horas.forEach((h, i) => {
      const r = Math.random();
      if (r > 0.35) {
        const p = PATIENTS[Math.floor(Math.random() * PATIENTS.length)];
        slots.push({
          profesional: prof.key, profNombre: prof.nombre, color: prof.color,
          hora: h, paciente: p.nombre, folio: p.folio,
          tipo: prof.key.startsWith('psi') ? pick(['Sesión psi.','Evaluación psi.','Seguimiento']) : pick(['Control médico','Evaluación','Primera atención']),
          estado: pick(['Confirmada','Confirmada','Confirmada','En espera','Pendiente']),
        });
      }
    });
  });
  return { profesionales, slots };
})();

// expose globals
Object.assign(window, {
  PATIENTS, LICENCIAS, RECETAS, CONTROLES, EPTS, REINTEGROS,
  ALERTS, DASHBOARD_KPIS, SERIE_INGRESOS, SERIE_ATENCIONES,
  CARGA_PROFESIONAL, AGENDA_SLOTS, REGIONES, MEDICOS, PSICOLOGOS,
  DIAGNOSTICOS, TIPOS_DERIVACION, ESTADOS, TIPOS_ALTA, EMPRESAS,
  fmtDate, fmtRut, addDays, diffDays
});
