/** Datos de prueba compartidos por los tests de Reportería. */
export const ODA_VENCIDA = {
  id: 21,
  folio_id: 14,
  identificador: "395331",
  folio: "F-2026-0057",
  paciente_nombre: "Paciente Prueba",
  paciente_rut: "11.111.111-1",
  fecha_registro: "2026-10-14",
  fecha_vencimiento: "2026-11-03",
  programa: "Programa Regular",
  region: "Maule",
  comuna: null,
  ordenes: [
    { identificador: "395331", tipo: "OPA", fecha_inicio: "2026-10-14", fecha_termino: "2026-11-03" },
  ],
  fechas_atencion: ["2026-10-20"],
  cobertura: "CUBRE",
  estado_gestion: "pendiente",
};

export function odasVencidasResp(items: object[]) {
  return { fecha_consulta: "2026-11-18", total: items.length, items };
}
