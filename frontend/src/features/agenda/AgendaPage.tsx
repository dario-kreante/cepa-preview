/**
 * AgendaPage — Agendamiento inteligente (EPIC-08, CEPA-080).
 *
 * Profesional-driven: se carga un profesional por id → se gestiona su
 * disponibilidad (días hábiles + cupo), se genera una propuesta automática
 * (diaria/semanal/mensual) y se revisan/confirman las citas candidatas
 * priorizadas (control vencido > próximo > seguimiento receta).
 *
 * RBAC: escritura = Administrativo + Coordinacion (puedeEscribir). Auditor lee.
 */
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { Calendar, Hash, Plus, CheckCircle2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn, fmtDate } from "@/lib/utils";
import { useAuth } from "@/lib/auth/AuthContext";
import { puedeEscribir, type Rol } from "@/lib/rbac";
import {
  useCitas,
  useConfirmarCitas,
  useCrearDisponibilidad,
  useDisponibilidad,
  useGenerarPropuesta,
  usePropuestas,
} from "./hooks";
import { propuestaSchema, type PropuestaForm } from "./propuestaSchema";
import type {
  CitaPropuestaRead,
  PrioridadCita,
  PropuestaAgendaRead,
} from "./api";

const DIA_LABELS: Record<number, string> = {
  1: "Lunes",
  2: "Martes",
  3: "Miércoles",
  4: "Jueves",
  5: "Viernes",
};

const PRIORIDAD_LABELS: Record<PrioridadCita, string> = {
  control_vencido: "Control vencido",
  control_proximo: "Control próximo",
  seguimiento_receta: "Seguimiento receta",
};

function prioridadVariant(
  p: PrioridadCita,
): "destructive" | "warning" | "info" {
  if (p === "control_vencido") return "destructive";
  if (p === "control_proximo") return "warning";
  return "info";
}

const ESTADO_PROP_VARIANT: Record<string, "info" | "success" | "neutral"> = {
  borrador: "info",
  confirmada: "success",
  descartada: "neutral",
};

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="text-left px-4 py-3 font-semibold text-[11px] uppercase tracking-wider text-muted-foreground">
      {children}
    </th>
  );
}

const selectCls =
  "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-[13px] shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-ring";

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
  const [dia, setDia] = useState("1");
  const [cupo, setCupo] = useState("4");

  async function add() {
    try {
      await crear.mutateAsync({
        profesional_id: profesionalId,
        dia_semana: parseInt(dia, 10) as 1 | 2 | 3 | 4 | 5,
        cupo_diario: parseInt(cupo, 10),
      });
      toast.success("Disponibilidad agregada");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    }
  }

  return (
    <Card className="p-5 space-y-3">
      <h3 className="text-[14px] font-semibold">Disponibilidad semanal</h3>
      {isLoading ? (
        <p className="text-[13px] text-muted-foreground">Cargando…</p>
      ) : dispo.length === 0 ? (
        <p className="text-[13px] text-muted-foreground">
          Sin disponibilidad registrada para este profesional.
        </p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {dispo.map((d) => (
            <Badge key={d.id} variant="neutral">
              {DIA_LABELS[d.dia_semana]} · {d.cupo_diario} cupos
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
            <Plus className="size-3.5" /> Agregar
          </Button>
        </div>
      )}
    </Card>
  );
}

// ── Citas de una propuesta ──────────────────────────────────────────────────────

function CitasPanel({
  propuesta,
  canWrite,
}: {
  propuesta: PropuestaAgendaRead;
  canWrite: boolean;
}) {
  const { data: citas = [], isLoading } = useCitas(propuesta.id);
  const confirmar = useConfirmarCitas();
  const [seleccion, setSeleccion] = useState<Set<number>>(new Set());

  function toggle(id: number) {
    setSeleccion((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function onConfirmar() {
    if (seleccion.size === 0) return;
    try {
      await confirmar.mutateAsync({
        propuestaId: propuesta.id,
        citaIds: [...seleccion],
      });
      toast.success(`${seleccion.size} cita(s) confirmada(s)`);
      setSeleccion(new Set());
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error al confirmar");
    }
  }

  return (
    <Card className="p-0 overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b">
        <h3 className="text-[14px] font-semibold">
          Citas candidatas · Propuesta N° {propuesta.id}
        </h3>
        {canWrite && (
          <Button
            size="sm"
            onClick={onConfirmar}
            disabled={seleccion.size === 0 || confirmar.isPending}
            data-testid="btn-confirmar-citas"
          >
            <CheckCircle2 className="size-3.5" /> Confirmar ({seleccion.size})
          </Button>
        )}
      </div>

      {isLoading ? (
        <p className="text-[13px] text-muted-foreground px-5 py-4">Cargando citas…</p>
      ) : citas.length === 0 ? (
        <p className="text-[13px] text-muted-foreground px-5 py-8 text-center">
          Esta propuesta no generó citas candidatas (sin controles vencidos /
          próximos ni seguimientos de receta en el rango).
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/30 border-b">
                {canWrite && <Th> </Th>}
                <Th>Fecha</Th>
                <Th>Paciente</Th>
                <Th>Prioridad</Th>
                <Th>Razón</Th>
                <Th>Estado</Th>
              </tr>
            </thead>
            <tbody>
              {citas.map((c: CitaPropuestaRead) => (
                <tr key={c.id} className="border-b" data-testid={`cita-${c.id}`}>
                  {canWrite && (
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={seleccion.has(c.id)}
                        onChange={() => toggle(c.id)}
                        disabled={c.estado !== "propuesta"}
                        aria-label={`Seleccionar cita ${c.id}`}
                      />
                    </td>
                  )}
                  <td className="px-4 py-3 font-mono text-[12px]">
                    {fmtDate(c.fecha_candidata)}
                  </td>
                  <td className="px-4 py-3 text-[13px]">
                    Paciente N° {c.paciente_id}
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={prioridadVariant(c.prioridad)}>
                      {PRIORIDAD_LABELS[c.prioridad]}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-[12.5px]">{c.razon}</td>
                  <td className="px-4 py-3 text-[12.5px] capitalize">
                    {c.estado}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function AgendaPage() {
  const { rol } = useAuth();
  const canWrite = puedeEscribir(rol as Rol);

  const [profIdInput, setProfIdInput] = useState("");
  const [profesionalId, setProfesionalId] = useState<number | null>(null);
  const [propuestaSel, setPropuestaSel] = useState<PropuestaAgendaRead | null>(
    null,
  );

  const { data: propuestas = [] } = usePropuestas(profesionalId);
  const generar = useGenerarPropuesta();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<PropuestaForm>({
    resolver: zodResolver(propuestaSchema),
    defaultValues: { tipo: "semanal", fecha_inicio: "" },
  });

  function cargarProfesional() {
    const n = parseInt(profIdInput, 10);
    if (!isNaN(n) && n > 0) {
      setProfesionalId(n);
      setPropuestaSel(null);
    }
  }

  async function onGenerar(v: PropuestaForm) {
    if (!profesionalId) return;
    try {
      const prop = await generar.mutateAsync({
        profesional_id: profesionalId,
        tipo: v.tipo,
        fecha_inicio: v.fecha_inicio,
        // fecha_fin la calcula el backend
        fecha_fin: v.fecha_inicio,
      });
      toast.success("Propuesta generada");
      setPropuestaSel(prop);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error al generar");
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight">
          Agendamiento inteligente
        </h1>
        <p className="text-[13px] text-muted-foreground mt-1">
          Propuesta automática de agenda según disponibilidad y prioridad clínica
        </p>
      </div>

      {/* Cargar profesional */}
      <div className="flex items-center gap-2">
        <Hash className="size-3.5 text-muted-foreground shrink-0" />
        <Input
          type="number"
          min={1}
          value={profIdInput}
          onChange={(e) => setProfIdInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") cargarProfesional();
          }}
          placeholder="ID profesional"
          className="h-9 w-[180px] text-[13px]"
          aria-label="ID del profesional"
          data-testid="input-prof-id"
        />
        <Button
          size="sm"
          variant="outline"
          onClick={cargarProfesional}
          disabled={!profIdInput}
          data-testid="btn-cargar-prof"
        >
          Cargar
        </Button>
      </div>

      {profesionalId === null ? (
        <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-12 text-center">
          <Calendar className="mx-auto mb-3 size-8 text-muted-foreground/50" />
          <p className="text-[13.5px] text-muted-foreground">
            Carga un profesional por su ID para gestionar disponibilidad y
            generar propuestas de agenda.
          </p>
        </div>
      ) : (
        <>
          <DisponibilidadCard profesionalId={profesionalId} canWrite={canWrite} />

          {/* Generar propuesta */}
          {canWrite && (
            <Card className="p-5">
              <form
                onSubmit={handleSubmit(onGenerar)}
                className="flex flex-wrap items-end gap-3"
              >
                <div>
                  <Label htmlFor="tipo">Tipo de propuesta</Label>
                  <select id="tipo" className={cn(selectCls, "w-40")} {...register("tipo")}>
                    <option value="diaria">Diaria</option>
                    <option value="semanal">Semanal</option>
                    <option value="mensual">Mensual</option>
                  </select>
                </div>
                <div>
                  <Label htmlFor="fecha_inicio">Fecha inicio (día hábil)</Label>
                  <Input
                    id="fecha_inicio"
                    type="date"
                    {...register("fecha_inicio")}
                  />
                  {errors.fecha_inicio && (
                    <p className="text-[11.5px] text-destructive mt-1">
                      {errors.fecha_inicio.message}
                    </p>
                  )}
                </div>
                <Button
                  type="submit"
                  disabled={generar.isPending}
                  data-testid="btn-generar-propuesta"
                >
                  <Calendar className="size-3.5" />
                  {generar.isPending ? "Generando…" : "Generar propuesta"}
                </Button>
              </form>
            </Card>
          )}

          {/* Propuestas existentes */}
          <div className="space-y-2">
            <h3 className="text-[14px] font-semibold px-0.5">
              Propuestas del profesional
            </h3>
            {propuestas.length === 0 ? (
              <p className="text-[13px] text-muted-foreground px-1">
                Sin propuestas generadas aún.
              </p>
            ) : (
              <Card className="overflow-hidden p-0">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-muted/30 border-b">
                      <Th>N°</Th>
                      <Th>Tipo</Th>
                      <Th>Período</Th>
                      <Th>Estado</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {propuestas.map((p) => (
                      <tr
                        key={p.id}
                        onClick={() => setPropuestaSel(p)}
                        className={cn(
                          "border-b cursor-pointer transition-colors",
                          propuestaSel?.id === p.id
                            ? "bg-primary/5 hover:bg-primary/10"
                            : "hover:bg-muted/40",
                        )}
                        data-testid={`row-propuesta-${p.id}`}
                      >
                        <td className="px-4 py-3 font-semibold text-[13px]">
                          {p.id}
                        </td>
                        <td className="px-4 py-3 text-[12.5px] capitalize">
                          {p.tipo}
                        </td>
                        <td className="px-4 py-3 font-mono text-[12px]">
                          {fmtDate(p.fecha_inicio)} → {fmtDate(p.fecha_fin)}
                        </td>
                        <td className="px-4 py-3">
                          <Badge
                            variant={ESTADO_PROP_VARIANT[p.estado] ?? "neutral"}
                            className="capitalize"
                          >
                            {p.estado}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            )}
          </div>

          {propuestaSel && (
            <CitasPanel propuesta={propuestaSel} canWrite={canWrite} />
          )}
        </>
      )}
    </div>
  );
}
