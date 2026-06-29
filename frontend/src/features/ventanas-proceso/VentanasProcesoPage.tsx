/**
 * VentanasProcesoPage — ventanas de visualización por proceso (CEPA-096, §7.10).
 *
 * Configura qué columnas se muestran (y el orden por defecto) para cada uno de
 * los 5 procesos: licencias, fármacos, auditoría, reintegro, controles.
 * Lectura: todos los roles. Alta: Coordinación y Administrativo.
 */
import { useState } from "react";
import { toast } from "sonner";
import { Plus, LayoutGrid } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { fmtDate } from "@/lib/utils";
import { useAuth } from "@/lib/auth/AuthContext";
import { puedeEscribir, type Rol } from "@/lib/rbac";
import { useVentanas, useCrearVentana } from "./hooks";
import { PROCESOS, PROCESO_LABELS, type Proceso } from "./api";

const selectCls =
  "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-[13px] shadow-sm focus:outline-none focus:ring-1 focus:ring-ring";

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="text-left px-4 py-3 font-semibold text-[11px] uppercase tracking-wider text-muted-foreground">
      {children}
    </th>
  );
}

export function VentanasProcesoPage() {
  const { rol } = useAuth();
  const canWrite = puedeEscribir(rol as Rol);
  const { data: ventanas = [], isLoading, isError, error } = useVentanas();
  const crear = useCrearVentana();

  const [proceso, setProceso] = useState<Proceso>("licencias");
  const [columnas, setColumnas] = useState("");
  const [orden, setOrden] = useState("");

  async function onCrear() {
    const cols = columnas
      .split(",")
      .map((c) => c.trim())
      .filter(Boolean);
    if (cols.length === 0) {
      toast.error("Indica al menos una columna visible.");
      return;
    }
    try {
      await crear.mutateAsync({
        proceso,
        columnas_visibles: cols,
        orden_por_defecto: orden.trim() || null,
      });
      toast.success("Ventana de proceso creada");
      setColumnas("");
      setOrden("");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-2">
        <LayoutGrid className="size-5 text-muted-foreground" />
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">
            Ventanas de proceso
          </h1>
          <p className="text-[13px] text-muted-foreground">
            Columnas visibles y orden por proceso · {canWrite ? "edición" : "solo lectura"}
          </p>
        </div>
      </div>

      {canWrite && (
        <Card className="p-5">
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <Label htmlFor="proceso">Proceso</Label>
              <select
                id="proceso"
                className={selectCls}
                style={{ width: 160 }}
                value={proceso}
                onChange={(e) => setProceso(e.target.value as Proceso)}
              >
                {PROCESOS.map((p) => (
                  <option key={p} value={p}>
                    {PROCESO_LABELS[p]}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex-1 min-w-[220px]">
              <Label htmlFor="columnas">Columnas visibles (separadas por coma)</Label>
              <Input
                id="columnas"
                value={columnas}
                onChange={(e) => setColumnas(e.target.value)}
                placeholder="folio, paciente, estado, fecha"
                className="h-9"
                data-testid="input-columnas"
              />
            </div>
            <div>
              <Label htmlFor="orden">Orden por defecto (opcional)</Label>
              <Input
                id="orden"
                value={orden}
                onChange={(e) => setOrden(e.target.value)}
                placeholder="fecha"
                className="h-9 w-[150px]"
              />
            </div>
            <Button
              size="sm"
              onClick={onCrear}
              disabled={crear.isPending}
              data-testid="btn-crear-ventana"
            >
              <Plus className="size-3.5" />
              {crear.isPending ? "Guardando…" : "Crear"}
            </Button>
          </div>
        </Card>
      )}

      {isError && (
        <p className="text-[13px] text-destructive px-1">
          {error instanceof Error ? error.message : "Error al cargar"}
        </p>
      )}

      {isLoading ? (
        <p className="text-[13px] text-muted-foreground px-1">Cargando…</p>
      ) : ventanas.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-12 text-center">
          <p className="text-[13.5px] text-muted-foreground">
            Sin ventanas configuradas todavía.
          </p>
        </div>
      ) : (
        <Card className="overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/30 border-b">
                  <Th>Proceso</Th>
                  <Th>Columnas visibles</Th>
                  <Th>Orden</Th>
                  <Th>Creado por</Th>
                  <Th>Fecha</Th>
                </tr>
              </thead>
              <tbody>
                {ventanas.map((v) => (
                  <tr
                    key={v.id}
                    className="border-b"
                    data-testid={`row-ventana-${v.id}`}
                  >
                    <td className="px-4 py-3">
                      <Badge variant="info">
                        {PROCESO_LABELS[v.proceso as Proceso] ?? v.proceso}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {v.columnas_visibles.map((c, i) => (
                          <Badge key={i} variant="neutral">
                            {c}
                          </Badge>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-[12.5px]">
                      {v.orden_por_defecto ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-[12.5px] text-muted-foreground">
                      {v.creado_por ?? "—"}
                    </td>
                    <td className="px-4 py-3 font-mono text-[12px] text-muted-foreground">
                      {fmtDate(v.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
