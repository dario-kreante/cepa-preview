/**
 * Pestaña ODAS de Reportería.
 *  - «Estado por paciente» (QA-006): todos los pacientes con el estado del caso y de la ODA.
 *  - «Vencidas» (QA-007): ODA vencidas y atendidos sin ODA, con cobertura (CUBRE / SOLICITAR), gestión editable,
 *    filtro por programa y descarga en Excel.
 */
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Download, FileText, Upload } from "lucide-react";
import { useAuth } from "@/lib/auth/AuthContext";
import { puedeEscribir, type Rol } from "@/lib/rbac";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { cn, fmtDate } from "@/lib/utils";
import { CargarReporteIslDialog } from "./CargarReporteIslDialog";
import type { EstadoGestion, ODAVencidaItem, ProgramaFiltro } from "./api";
import {
  useCambiarGestionOda,
  useDescargarOdasExcel,
  useReporteOdasEstado,
  useReporteOdasVencidas,
} from "./hooks";

const SELECT_CLS =
  "h-9 pl-3 pr-8 text-[12.5px] border rounded-md bg-card hover:bg-muted/30 cursor-pointer focus:outline-none focus:ring-2 focus:ring-ring font-medium";
const SEP = " / ";
const SIN_DATO = "—";

const PROGRAMAS: [ProgramaFiltro | "", string][] = [
  ["", "Todos"],
  ["regular", "Regular"],
  ["ingreso_isl", "Ingreso ISL"],
  ["tratamiento_isl", "Tratamiento ISL"],
  ["ley_karin", "Ley Karin"],
  ["pipt", "PIPT"],
];
const GESTION: [EstadoGestion, string][] = [
  ["pendiente", "Pendiente"],
  ["solicitada", "Solicitada"],
  ["recibida", "Recibida"],
];
const ESTADOS_CASO: [string, string][] = [
  ["", "Todos"],
  ["activo", "Activo"],
  ["cerrado", "Cerrado"],
  ["encuadre", "Encuadre"],
  ["derivado", "Derivado"],
];
const NOMBRE_CASO = Object.fromEntries(ESTADOS_CASO.filter(([k]) => k));

const unir = (v: string[]) => (v.length ? v.join(SEP) : SIN_DATO);
const fecha = (d: string | null | undefined) => (d ? fmtDate(d) : SIN_DATO);

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="text-left px-4 py-2.5 font-semibold text-[11px] uppercase tracking-wider text-muted-foreground">
      {children}
    </th>
  );
}

function Vacio({ texto }: { texto: string }) {
  return (
    <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-10 text-center">
      <p className="text-[13.5px] text-muted-foreground">{texto}</p>
    </div>
  );
}

function BadgeOda({ estado }: { estado: string }) {
  const [variante, texto] =
    estado === "vencida"
      ? (["destructive", "Vencida"] as const)
      : estado === "por_vencer"
        ? (["warning", "Por vencer"] as const)
        : estado === "vigente"
          ? (["success", "Vigente"] as const)
          : (["neutral", "Sin ODA"] as const);
  return <Badge variant={variante}>{texto}</Badge>;
}

function venceEn(dias: number | null): string {
  if (dias == null) return SIN_DATO;
  if (dias === 0) return "hoy";
  if (dias > 0) return `en ${dias} ${dias === 1 ? "día" : "días"}`;
  return `hace ${-dias} ${dias === -1 ? "día" : "días"}`;
}

// ── QA-006 ──────────────────────────────────────────────────────────────────────

function EstadoPorPaciente() {
  const m = useReporteOdasEstado();
  const [estadoCaso, setEstadoCaso] = useState("");

  async function consultar() {
    try {
      await m.mutateAsync(estadoCaso || undefined);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    }
  }

  return (
    <div className="space-y-3">
      <Card className="p-4">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <Label htmlFor="f-estado-caso">Estado del caso</Label>
            <select
              id="f-estado-caso"
              data-testid="filtro-estado-caso"
              value={estadoCaso}
              onChange={(e) => setEstadoCaso(e.target.value)}
              className={cn(SELECT_CLS, "block")}
            >
              {ESTADOS_CASO.map(([v, t]) => (
                <option key={v} value={v}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <Button size="sm" onClick={consultar} disabled={m.isPending} data-testid="btn-generar-reporte">
            <FileText className="size-3.5" />
            {m.isPending ? "Consultando…" : "Consultar"}
          </Button>
          <p className="text-[12px] text-muted-foreground">
            Estado de la ODA vigente de cada paciente. «Por vencer» = vence en{" "}
            {m.data?.dias_por_vencer ?? 15} días o menos.
          </p>
        </div>
      </Card>
      {m.data &&
        (m.data.items.length === 0 ? (
          <Vacio texto="No hay pacientes para el filtro elegido." />
        ) : (
          <Card className="overflow-hidden p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-muted/30 border-b">
                    {["Paciente", "RUT", "Folio", "Fecha de ingreso", "Estado del caso", "Estado de la ODA", "Vencimiento", "Vence"].map(
                      (h) => (
                        <Th key={h}>{h}</Th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody>
                  {m.data.items.map((it) => (
                    <tr key={it.ingreso_id} className="border-b">
                      <td className="px-4 py-2.5 text-[13px]">{it.paciente_nombre}</td>
                      <td className="px-4 py-2.5 text-[13px]">{it.paciente_rut ?? SIN_DATO}</td>
                      <td className="px-4 py-2.5 text-[13px]">{it.folio}</td>
                      <td className="px-4 py-2.5 text-[13px]">{fecha(it.fecha_ingreso)}</td>
                      <td className="px-4 py-2.5 text-[13px]">
                        {NOMBRE_CASO[it.estado_caso] ?? it.estado_caso}
                      </td>
                      <td className="px-4 py-2.5 text-[13px]">
                        <BadgeOda estado={it.estado_oda} />
                      </td>
                      <td className="px-4 py-2.5 text-[13px]">{fecha(it.fecha_vencimiento)}</td>
                      <td className="px-4 py-2.5 text-[13px]">
                        {it.estado_oda === "sin_oda" ? SIN_DATO : venceEn(it.dias_para_vencer)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        ))}
    </div>
  );
}

// ── QA-007 ──────────────────────────────────────────────────────────────────────

function FilaVencida({
  it,
  gestion,
  editable,
  onCambiar,
}: {
  it: ODAVencidaItem;
  gestion: EstadoGestion;
  editable: boolean;
  onCambiar: (odaId: number, estado: EstadoGestion) => void;
}) {
  // Sin id no hay ODA donde guardar la gestión (atendido sin ODA): se muestra «—».
  const odaId = it.id;
  const ordenes = it.ordenes?.length
    ? it.ordenes
    : it.identificador == null
      ? []
      : [{ identificador: it.identificador, tipo: null, fecha_inicio: it.fecha_registro, fecha_termino: it.fecha_vencimiento ?? SIN_DATO }];
  const cubre = (it.cobertura ?? "SOLICITAR") === "CUBRE";
  return (
    <tr className="border-b">
      <td className="px-4 py-2.5 text-[13px]">{it.paciente_nombre}</td>
      <td className="px-4 py-2.5 text-[13px]">{it.paciente_rut ?? SIN_DATO}</td>
      <td className="px-4 py-2.5 text-[13px]">{unir(ordenes.map((o) => o.identificador))}</td>
      <td className="px-4 py-2.5 text-[13px]">{unir(ordenes.map((o) => o.tipo ?? SIN_DATO))}</td>
      <td className="px-4 py-2.5 text-[13px]">{unir(ordenes.map((o) => fecha(o.fecha_inicio)))}</td>
      <td className="px-4 py-2.5 text-[13px]">{unir(ordenes.map((o) => fecha(o.fecha_termino)))}</td>
      <td className="px-4 py-2.5 text-[13px]">{unir((it.fechas_atencion ?? []).map((d) => fecha(d)))}</td>
      <td className="px-4 py-2.5 text-[13px]">
        <Badge variant={cubre ? "success" : "destructive"}>{cubre ? "CUBRE" : "SOLICITAR"}</Badge>
      </td>
      <td className="px-4 py-2.5 text-[13px]">
        {odaId == null ? (
          SIN_DATO
        ) : editable ? (
          <select
            data-testid={`gestion-${odaId}`}
            aria-label={`Estado de gestión de ${it.paciente_nombre}`}
            value={gestion}
            onChange={(e) => onCambiar(odaId, e.target.value as EstadoGestion)}
            className={SELECT_CLS}
          >
            {GESTION.map(([v, t]) => (
              <option key={v} value={v}>
                {t}
              </option>
            ))}
          </select>
        ) : (
          <span data-testid={`gestion-${odaId}`}>
            {GESTION.find(([v]) => v === gestion)?.[1] ?? gestion}
          </span>
        )}
      </td>
    </tr>
  );
}

function Vencidas({ autoCargar }: { autoCargar: boolean }) {
  const m = useReporteOdasVencidas();
  const cambiar = useCambiarGestionOda();
  const excel = useDescargarOdasExcel();
  const { rol } = useAuth();
  const [programa, setPrograma] = useState<ProgramaFiltro | "">("");
  const [cargaAbierta, setCargaAbierta] = useState(false);
  // Gestión cambiada en esta sesión (se ve de inmediato; el backend es la fuente de verdad).
  const [gestion, setGestion] = useState<Record<number, EstadoGestion>>({});

  async function consultar() {
    try {
      await m.mutateAsync(programa || undefined);
      setGestion({});
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    }
  }

  useEffect(() => {
    // Llegar por el enlace del dashboard (?tab=odas) carga el informe sin apretar «Consultar».
    // Se difiere y se cancela al desmontar: StrictMode monta dos veces, y una consulta lanzada
    // en el primer montaje dejaría el botón en «Consultando…» para siempre.
    if (!autoCargar) return;
    const temporizador = setTimeout(() => void consultar(), 0);
    return () => clearTimeout(temporizador);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function cambiarGestion(odaId: number, estado: EstadoGestion) {
    try {
      await cambiar.mutateAsync({ odaId, estado });
      setGestion((g) => ({ ...g, [odaId]: estado }));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    }
  }

  async function descargar() {
    try {
      await excel.mutateAsync(programa || undefined);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    }
  }

  const editable = puedeEscribir(rol as Rol);
  return (
    <div className="space-y-3">
      <Card className="p-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <Label htmlFor="f-programa">Programa</Label>
              <select
                id="f-programa"
                data-testid="filtro-programa"
                value={programa}
                onChange={(e) => setPrograma(e.target.value as ProgramaFiltro | "")}
                className={cn(SELECT_CLS, "block")}
              >
                {PROGRAMAS.map(([v, t]) => (
                  <option key={v} value={v}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
            <p className="max-w-md text-[12.5px] text-muted-foreground">
              ODAS vigentes de casos activos con fecha de vencimiento pasada a hoy. También incluye a
              los pacientes atendidos sin ODA registrada (SOLICITAR, sin gestión). CUBRE = todas las
              atenciones tienen una ODA/OPA vigente ese día.
            </p>
          </div>
          <div className="flex gap-2">
            {editable && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => setCargaAbierta(true)}
                data-testid="btn-cargar-reporte-isl"
              >
                <Upload className="size-3.5" />
                Cargar reporte ISL
              </Button>
            )}
            <Button
              size="sm"
              variant="outline"
              onClick={descargar}
              disabled={excel.isPending}
              data-testid="btn-excel-odas"
            >
              <Download className="size-3.5" />
              {excel.isPending ? "Descargando…" : "Descargar Excel"}
            </Button>
            <Button size="sm" onClick={consultar} disabled={m.isPending} data-testid="btn-generar-reporte">
              <FileText className="size-3.5" />
              {m.isPending ? "Consultando…" : "Consultar"}
            </Button>
          </div>
        </div>
      </Card>
      <CargarReporteIslDialog open={cargaAbierta} onOpenChange={setCargaAbierta} />
      {m.data &&
        (m.data.items.length === 0 ? (
          <Vacio texto="No hay ODAS vencidas ni pacientes atendidos sin ODA." />
        ) : (
          <Card className="overflow-hidden p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-muted/30 border-b">
                    {["Nombre", "RUT", "N° ODA/OPA", "Tipo", "Fecha inicio", "Fecha término", "Fechas de atención", "Cobertura", "Gestión"].map(
                      (h) => (
                        <Th key={h}>{h}</Th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody>
                  {m.data.items.map((it) => (
                    <FilaVencida
                      key={`${it.folio_id}-${it.id ?? "sin-oda"}`}
                      it={it}
                      gestion={(it.id != null ? gestion[it.id] : undefined) ?? it.estado_gestion ?? "pendiente"}
                      editable={editable}
                      onCambiar={cambiarGestion}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        ))}
    </div>
  );
}

// ── Pestaña ─────────────────────────────────────────────────────────────────────

export function OdasTab({ autoCargar }: { autoCargar: boolean }) {
  // Llegar por el enlace de la tarjeta «ODA vencidas» abre esa vista ya cargada.
  const [vista, setVista] = useState<"estado" | "vencidas">(autoCargar ? "vencidas" : "estado");
  const vistas: ["estado" | "vencidas", string][] = [
    ["estado", "Estado por paciente"],
    ["vencidas", "ODA vencidas"],
  ];
  return (
    <div className="space-y-3">
      <div className="inline-flex rounded-md border p-0.5 bg-muted/30" role="group" aria-label="Vista de ODAS">
        {vistas.map(([k, t]) => (
          <button
            key={k}
            type="button"
            data-testid={`vista-${k}`}
            aria-pressed={vista === k}
            onClick={() => setVista(k)}
            className={cn(
              "px-3 py-1.5 text-[12.5px] font-medium rounded",
              vista === k ? "bg-card shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {t}
          </button>
        ))}
      </div>
      {vista === "estado" ? <EstadoPorPaciente /> : <Vencidas autoCargar={autoCargar} />}
    </div>
  );
}
