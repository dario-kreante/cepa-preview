/** Fecha local en formato AAAA-MM-DD, comparable con las fechas que entrega la API. */
function hoyLocal(): string {
  const d = new Date();
  const mes = String(d.getMonth() + 1).padStart(2, "0");
  const dia = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${mes}-${dia}`;
}

/**
 * Si el control tiene un próximo control agendado que todavía no pasa. `proximo_agendado`
 * queda en true para siempre en los controles antiguos: sin mirar la fecha, un control de
 * 2022 se ve «Agendado» y parece que no se hubiera atendido (QA-003, QA UTalca 29-10).
 */
export function proximoAgendadoVigente(
  control: { proximo_agendado?: boolean | null; proximo_control?: string | null },
  hoy: string = hoyLocal(),
): boolean {
  return !!control.proximo_agendado && !!control.proximo_control && control.proximo_control >= hoy;
}
