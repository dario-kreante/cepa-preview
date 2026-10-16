/**
 * AgendaPage — Pacientes por citar.
 *
 * El SIGE ya no agenda: las horas se agendan en SALUTEM y un paciente sale de la lista
 * cuando SALUTEM tiene una hora vigente. Esta pantalla es la lista de trabajo del
 * profesional elegido: quién falta citar, con qué prioridad, en qué día sugerido, y el
 * registro de cada intento de contacto.
 *
 * RBAC: escritura = Administrativo + Coordinacion (puedeEscribir). Auditor lee.
 */
import { useState } from "react";
import { toast } from "sonner";
import { Link } from "react-router-dom";
import {
  Calendar,
  ChevronDown,
  ChevronRight,
  Phone,
  Plus,
  UserRound,
  X,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn, fmtDate } from "@/lib/utils";
import { useAuth } from "@/lib/auth/AuthContext";
import { puedeEscribir, type Rol } from "@/lib/rbac";
import { useProfesionales } from "@/features/profesionales/hooks";
import {
  useCrearDisponibilidad,
  useDisponibilidad,
  usePacientesPorCitar,
  useQuitarDisponibilidad,
  type RangoAgenda,
} from "./hooks";
import {
  RESULTADO_LABELS,
  type CargaDiaRead,
  type PacientePorCitarRead,
  type PrioridadCita,
} from "./api";
import {
  RegistrarContactoDialog,
  type PacienteContacto,
} from "./RegistrarContactoDialog";

const DIA_LABELS: Record<number, string> = {
  1: "Lunes",
  2: "Martes",
  3: "Miércoles",
  4: "Jueves",
  5: "Viernes",
};

const DIA_CORTO = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];

const PRIORIDAD_LABELS: Record<PrioridadCita, string> = {
  control_vencido: "Control vencido",
  control_proximo: "Control próximo",
  seguimiento_receta: "Seguimiento receta",
};

const RANGO_LABELS: Record<RangoAgenda, string> = {
  semana: "Esta semana",
  dos_semanas: "Dos semanas",
  mes: "Este mes",
};

function prioridadVariant(
  p: PrioridadCita,
): "destructive" | "warning" | "info" {
  if (p === "control_vencido") return "destructive";
  if (p === "control_proximo") return "warning";
  return "info";
}

/** "2026-10-14" -> "Mié 14" (sin pasar por zona horaria). */
function chipDia(fecha: string): string {
  const [y, m, d] = fecha.split("-").map(Number);
  return `${DIA_CORTO[new Date(y, m - 1, d).getDay()]} ${d}`;
}

const FORMATO_DIA_MES = new Intl.DateTimeFormat("es-CL", {
  timeZone: "America/Santiago",
  day: "2-digit",
  month: "2-digit",
});

/** Fecha/hora ISO (UTC) -> "15-10" (día-mes) en hora de Santiago. */
function diaMes(iso: string): string {
  const partes = FORMATO_DIA_MES.formatToParts(new Date(iso));
  const dia = partes.find((p) => p.type === "day")?.value ?? "";
  const mes = partes.find((p) => p.type === "month")?.value ?? "";
  return `${dia}-${mes}`;
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="text-left px-4 py-3 font-semibold text-[11px] uppercase tracking-wider text-muted-foreground">
      {children}
    </th>
  );
}

const selectCls =
  "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-[13px] shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-ring";

function Plegable({
  titulo,
  defaultOpen = false,
  children,
}: {
  titulo: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [abierto, setAbierto] = useState(defaultOpen);
  const Icono = abierto ? ChevronDown : ChevronRight;
  return (
    <div className="space-y-2">
      <button
        type="button"
        onClick={() => setAbierto((v) => !v)}
        aria-expanded={abierto}
        className="flex items-center gap-1.5 px-0.5 text-[14px] font-semibold"
      >
        <Icono className="size-4 text-muted-foreground" />
        {titulo}
      </button>
      {abierto && children}
    </div>
  );
}

// ── Carga por día ───────────────────────────────────────────────────────────────

function FranjaCarga({
  dias,
  feriados,
}: {
  dias: CargaDiaRead[];
  feriados: string[];
}) {
  const chips = [
    ...dias.map((d) => ({ fecha: d.fecha, carga: d })),
    ...feriados.map((fecha) => ({ fecha, carga: null })),
  ].sort((a, b) => a.fecha.localeCompare(b.fecha));
  if (chips.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-2" aria-label="Carga por día">
      {chips.map(({ fecha, carga }) =>
        carga ? (
          <Badge
            key={fecha}
            variant={carga.asignados >= carga.cupo ? "warning" : "neutral"}
          >
            {chipDia(fecha)} · {carga.asignados}/{carga.cupo}
          </Badge>
        ) : (
          <Badge key={fecha} variant="info">
            {chipDia(fecha)} · Feriado
          </Badge>
        ),
      )}
    </div>
  );
}

// ── Tabla de pacientes ──────────────────────────────────────────────────────────

function TablaPacientes({
  pacientes,
  canWrite,
  onContactar,
  vacio,
}: {
  pacientes: PacientePorCitarRead[];
  canWrite: boolean;
  onContactar: (p: PacienteContacto) => void;
  vacio: string;
}) {
  if (pacientes.length === 0) {
    return <p className="text-[13px] text-muted-foreground px-1">{vacio}</p>;
  }
  return (
    <Card className="overflow-hidden p-0">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-muted/30 border-b">
            <Th>Paciente</Th>
            <Th>Prioridad</Th>
            <Th>Fecha objetivo</Th>
            <Th>Día sugerido</Th>
            <Th>Último contacto</Th>
            {canWrite && <Th>Acción</Th>}
          </tr>
        </thead>
        <tbody>
          {pacientes.map((p) => (
            <tr
              key={p.paciente_id}
              className="border-b"
              data-testid={`row-paciente-${p.paciente_id}`}
            >
              <td className="px-4 py-3">
                <div className="font-semibold text-[13px]">{p.nombre}</div>
                {p.folio && (
                  <div className="font-mono text-[11.5px] text-muted-foreground">
                    {p.folio}
                  </div>
                )}
                <div className="mt-1 flex flex-wrap gap-1">
                  {p.sin_vinculo_salutem && (
                    <Badge variant="warning">Sin vínculo SALUTEM</Badge>
                  )}
                  {p.dijo_agendada_sin_hora && (
                    <Badge variant="purple">
                      Dijo agendada, sin hora en SALUTEM
                    </Badge>
                  )}
                  {p.reposo_hasta && (
                    <Badge variant="info">
                      En reposo hasta {fmtDate(p.reposo_hasta)}
                    </Badge>
                  )}
                </div>
              </td>
              <td className="px-4 py-3">
                <Badge variant={prioridadVariant(p.prioridad)}>
                  {PRIORIDAD_LABELS[p.prioridad]}
                </Badge>
                <div className="mt-1 text-[12px] text-muted-foreground">
                  {p.razon}
                </div>
              </td>
              <td className="px-4 py-3 font-mono text-[12px]">
                {p.fecha_objetivo ? fmtDate(p.fecha_objetivo) : "—"}
              </td>
              <td className="px-4 py-3 font-mono text-[12px]">
                {p.dia_sugerido ? fmtDate(p.dia_sugerido) : "—"}
              </td>
              <td className="px-4 py-3 text-[12.5px]">
                {p.ultima_gestion
                  ? `${RESULTADO_LABELS[p.ultima_gestion.resultado]} · ${diaMes(p.ultima_gestion.fecha)} · ${p.ultima_gestion.usuario}`
                  : "—"}
              </td>
              {canWrite && (
                <td className="px-4 py-3">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() =>
                      onContactar({
                        paciente_id: p.paciente_id,
                        nombre: p.nombre,
                      })
                    }
                  >
                    <Phone className="size-3.5" /> Registrar contacto
                  </Button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

// ── Disponibilidad ────────────────────────────────────────────────────────────

function DisponibilidadCard({
  profesionalId,
  canWrite,
}: {
  profesionalId: number;
  canWrite: boolean;
}) {
  const { data: dispo = [], isLoading } = useDisponibilidad(profesionalId);
  const crear = useCrearDisponibilidad();
  const quitar = useQuitarDisponibilidad();
  const [dia, setDia] = useState("1");
  const [cupo, setCupo] = useState("4");

  async function add() {
    try {
      await crear.mutateAsync({
        profesional_id: profesionalId,
        dia_semana: parseInt(dia, 10) as 1 | 2 | 3 | 4 | 5,
        cupo_diario: parseInt(cupo, 10),
      });
      toast.success("Disponibilidad guardada");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    }
  }

  async function quitarDia(id: number) {
    try {
      await quitar.mutateAsync(id);
      toast.success("Disponibilidad quitada");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    }
  }

  return (
    <Plegable titulo="Disponibilidad semanal" defaultOpen>
      <Card className="p-5 space-y-3">
        {isLoading ? (
          <p className="text-[13px] text-muted-foreground">Cargando…</p>
        ) : dispo.length === 0 ? (
          <p className="text-[13px] text-muted-foreground">
            Sin disponibilidad registrada para este profesional.
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {dispo.map((d) => (
              <Badge key={d.id} variant="neutral" className="gap-1.5">
                {DIA_LABELS[d.dia_semana]} · {d.cupo_diario} cupos
                {canWrite && (
                  <button
                    type="button"
                    aria-label={`Quitar ${DIA_LABELS[d.dia_semana]}`}
                    onClick={() => quitarDia(d.id)}
                    disabled={quitar.isPending}
                    className="rounded-sm hover:text-destructive"
                  >
                    <X className="size-3" />
                  </button>
                )}
              </Badge>
            ))}
          </div>
        )}

        {canWrite && (
          <div className="flex flex-wrap items-end gap-2 pt-1">
            <div>
              <Label htmlFor="dia">Día</Label>
              <select
                id="dia"
                className={cn(selectCls, "w-[130px]")}
                value={dia}
                onChange={(e) => setDia(e.target.value)}
              >
                {[1, 2, 3, 4, 5].map((n) => (
                  <option key={n} value={n}>
                    {DIA_LABELS[n]}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label htmlFor="cupo">Cupo diario</Label>
              <Input
                id="cupo"
                type="number"
                min={1}
                value={cupo}
                onChange={(e) => setCupo(e.target.value)}
                className="h-9 w-[110px]"
              />
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={add}
              disabled={crear.isPending}
              data-testid="btn-add-dispo"
            >
              <Plus className="size-3.5" /> Guardar día
            </Button>
          </div>
        )}
      </Card>
    </Plegable>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function AgendaPage() {
  const { rol } = useAuth();
  const canWrite = puedeEscribir(rol as Rol);

  const [profesionalId, setProfesionalId] = useState<number | null>(null);
  const [rango, setRango] = useState<RangoAgenda>("dos_semanas");
  const [contacto, setContacto] = useState<PacienteContacto | null>(null);

  const { data: profesionales = [], isLoading: cargandoProfesionales } =
    useProfesionales(true);
  const {
    data: lista,
    isLoading: cargandoLista,
    isError,
  } = usePacientesPorCitar(profesionalId, rango);
  const { data: dispo, isSuccess: dispoCargada } =
    useDisponibilidad(profesionalId);

  const pacientes = lista?.pacientes ?? [];
  const porCitar = pacientes.filter((p) => p.seccion === "por_citar");
  const sinCupo = pacientes.filter((p) => p.seccion === "sin_cupo");
  const enReposo = pacientes.filter((p) => p.seccion === "en_reposo");

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight">
          Pacientes por citar
        </h1>
        <p className="text-[13px] text-muted-foreground mt-1">
          Las horas se agendan en SALUTEM; un paciente sale de la lista cuando
          SALUTEM tiene una hora vigente.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <UserRound className="size-3.5 text-muted-foreground shrink-0" />
        <select
          value={profesionalId ?? ""}
          onChange={(e) =>
            setProfesionalId(e.target.value ? Number(e.target.value) : null)
          }
          className={cn(selectCls, "w-[320px]")}
          aria-label="Profesional"
          disabled={cargandoProfesionales}
          data-testid="select-profesional"
        >
          <option value="">
            {cargandoProfesionales
              ? "Cargando profesionales…"
              : "Selecciona un profesional"}
          </option>
          {profesionales.map((p) => (
            <option key={p.id} value={p.id}>
              {p.especialidad ? `${p.nombre} · ${p.especialidad}` : p.nombre}
            </option>
          ))}
        </select>
        <select
          value={rango}
          onChange={(e) => setRango(e.target.value as RangoAgenda)}
          className={cn(selectCls, "w-[160px]")}
          aria-label="Rango"
        >
          {(Object.keys(RANGO_LABELS) as RangoAgenda[]).map((r) => (
            <option key={r} value={r}>
              {RANGO_LABELS[r]}
            </option>
          ))}
        </select>
        {canWrite && (
          <Link
            to="/profesionales"
            className="text-[12.5px] text-primary hover:underline"
          >
            Gestionar profesionales
          </Link>
        )}
      </div>

      {profesionalId === null ? (
        <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-12 text-center">
          <Calendar className="mx-auto mb-3 size-8 text-muted-foreground/50" />
          <p className="text-[13.5px] text-muted-foreground">
            {!cargandoProfesionales && profesionales.length === 0
              ? "No hay profesionales activos en el catálogo."
              : "Elige un profesional para ver sus pacientes por citar."}
          </p>
        </div>
      ) : (
        <>
          {dispoCargada && dispo.length === 0 && (
            <div
              role="status"
              className="rounded-md border border-[oklch(0.85_0.1_85)] bg-[oklch(0.97_0.05_85)] px-4 py-2.5 text-[13px] text-[oklch(0.42_0.14_75)]"
            >
              Este profesional no tiene disponibilidad cargada: todos sus
              pacientes aparecen como sin cupo.
            </div>
          )}

          {lista && (
            <FranjaCarga dias={lista.por_dia} feriados={lista.feriados} />
          )}

          {isError ? (
            <p className="text-[13px] text-destructive">
              No se pudo cargar la lista de pacientes por citar.
            </p>
          ) : cargandoLista ? (
            <p className="text-[13px] text-muted-foreground">Cargando…</p>
          ) : (
            <>
              <div className="space-y-2">
                <h3 className="text-[14px] font-semibold px-0.5">
                  Por citar ({porCitar.length})
                </h3>
                <TablaPacientes
                  pacientes={porCitar}
                  canWrite={canWrite}
                  onContactar={setContacto}
                  vacio="No hay pacientes por citar en este período."
                />
              </div>

              <Plegable titulo={`Sin cupo en el período (${sinCupo.length})`}>
                <TablaPacientes
                  pacientes={sinCupo}
                  canWrite={canWrite}
                  onContactar={setContacto}
                  vacio="Ningún paciente quedó sin cupo."
                />
              </Plegable>

              <Plegable titulo={`En reposo (${enReposo.length})`}>
                <TablaPacientes
                  pacientes={enReposo}
                  canWrite={canWrite}
                  onContactar={setContacto}
                  vacio="Ningún paciente en reposo."
                />
              </Plegable>
            </>
          )}

          <DisponibilidadCard
            profesionalId={profesionalId}
            canWrite={canWrite}
          />

          <RegistrarContactoDialog
            paciente={contacto}
            profesionalId={profesionalId}
            onClose={() => setContacto(null)}
          />
        </>
      )}
    </div>
  );
}
