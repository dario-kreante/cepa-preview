/**
 * ConfigAlertasPage — umbrales de alerta y festivos (COMP-2609-07). Solo Coordinación.
 *
 * Edita, por tipo de alerta, la ventana de aviso (días), si se cuenta en días hábiles y si
 * el tipo está activo; y administra el calendario de festivos que descuenta el conteo de
 * días hábiles. El job diario lee estos valores en cada ejecución: no requiere despliegue.
 */
import { useState } from "react";
import { toast } from "sonner";
import { BellRing, Plus, ShieldCheck, Trash2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { fmtDate } from "@/lib/utils";
import { useAuth } from "@/lib/auth/AuthContext";
import type { Rol } from "@/lib/rbac";
import {
  useConfigAlertas,
  useCrearFestivo,
  useEliminarFestivo,
  useFestivos,
  useGuardarConfig,
} from "./hooks";
import { TIPO_LABELS, type ConfigAlertaItem, type ConfigAlertaRead } from "./api";

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="text-left px-4 py-3 font-semibold text-[11px] uppercase tracking-wider text-muted-foreground">
      {children}
    </th>
  );
}

export function ConfigAlertasPage() {
  const { rol } = useAuth();
  if ((rol as Rol) !== "Coordinacion") {
    return (
      <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-16 text-center">
        <ShieldCheck className="mx-auto mb-3 size-8 text-muted-foreground/50" />
        <p className="text-[13.5px] text-muted-foreground">
          La configuración de alertas está restringida al perfil Coordinación.
        </p>
      </div>
    );
  }
  return (
    <div className="space-y-5">
      <div className="flex items-center gap-2">
        <BellRing className="size-5 text-muted-foreground" />
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">Umbrales de alerta</h1>
          <p className="text-[13px] text-muted-foreground">
            Anticipación por tipo de alerta y festivos · aplica en la siguiente ejecución del job
          </p>
        </div>
      </div>
      <UmbralesCard />
      <FestivosCard />
    </div>
  );
}

function UmbralesCard() {
  const { data, isLoading, isError, error } = useConfigAlertas();
  if (isError) {
    return (
      <p className="text-[13px] text-destructive px-1">
        {error instanceof Error ? error.message : "Error al cargar"}
      </p>
    );
  }
  if (isLoading || !data) return <p className="text-[13px] text-muted-foreground px-1">Cargando…</p>;
  return <UmbralesForm inicial={data} />;
}

function UmbralesForm({ inicial }: { inicial: ConfigAlertaRead[] }) {
  const guardar = useGuardarConfig();
  const [filas, setFilas] = useState<ConfigAlertaItem[]>(() =>
    inicial.map(({ tipo, dias, habiles, activo }) => ({ tipo, dias, habiles, activo })),
  );

  function cambiar(tipo: string, cambio: Partial<ConfigAlertaItem>) {
    setFilas((prev) => prev.map((f) => (f.tipo === tipo ? { ...f, ...cambio } : f)));
  }

  async function onGuardar() {
    if (filas.some((f) => !Number.isInteger(f.dias) || f.dias < 0 || f.dias > 365)) {
      toast.error("Los días deben ser un entero entre 0 y 365.");
      return;
    }
    try {
      await guardar.mutateAsync(filas);
      toast.success("Umbrales guardados");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    }
  }

  return (
    <Card className="overflow-hidden p-0">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-muted/30 border-b">
              <Th>Tipo de alerta</Th>
              <Th>Días de anticipación</Th>
              <Th>Días hábiles</Th>
              <Th>Activo</Th>
            </tr>
          </thead>
          <tbody>
            {filas.map((f) => {
              const nombre = TIPO_LABELS[f.tipo] ?? f.tipo;
              return (
                <tr key={f.tipo} className="border-b" data-testid={`fila-${f.tipo}`}>
                  <td className="px-4 py-3 font-medium">{nombre}</td>
                  <td className="px-4 py-3">
                    <Input
                      type="number"
                      min={0}
                      max={365}
                      aria-label={`Días ${nombre}`}
                      className="h-8 w-[90px]"
                      value={Number.isNaN(f.dias) ? "" : f.dias}
                      onChange={(e) => cambiar(f.tipo, { dias: e.target.valueAsNumber })}
                    />
                  </td>
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      aria-label={`Hábiles ${nombre}`}
                      checked={f.habiles}
                      onChange={(e) => cambiar(f.tipo, { habiles: e.target.checked })}
                    />
                  </td>
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      aria-label={`Activo ${nombre}`}
                      checked={f.activo}
                      onChange={(e) => cambiar(f.tipo, { activo: e.target.checked })}
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between gap-3 px-4 py-3">
        <p className="text-[12px] text-muted-foreground">
          Valores iniciales provisorios hasta la confirmación de Coordinación (COMP-2609-13).
        </p>
        <Button size="sm" onClick={onGuardar} disabled={guardar.isPending}>
          {guardar.isPending ? "Guardando…" : "Guardar umbrales"}
        </Button>
      </div>
    </Card>
  );
}

function FestivosCard() {
  const { data: festivos = [], isLoading, isError, error } = useFestivos();
  const crear = useCrearFestivo();
  const eliminar = useEliminarFestivo();
  const [fecha, setFecha] = useState("");
  const [descripcion, setDescripcion] = useState("");

  async function onAgregar() {
    if (!fecha || !descripcion.trim()) {
      toast.error("Indica la fecha y la descripción del festivo.");
      return;
    }
    try {
      await crear.mutateAsync({ fecha, descripcion: descripcion.trim() });
      toast.success("Festivo agregado");
      setFecha("");
      setDescripcion("");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    }
  }

  async function onEliminar(id: number) {
    try {
      await eliminar.mutateAsync(id);
      toast.success("Festivo eliminado");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    }
  }

  return (
    <Card className="p-5 space-y-4">
      <div>
        <h2 className="text-[15px] font-semibold">Festivos</h2>
        <p className="text-[12.5px] text-muted-foreground">
          Días no hábiles además de sábados y domingos.
        </p>
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <Label htmlFor="festivo-fecha">Fecha</Label>
          <Input
            id="festivo-fecha"
            type="date"
            className="h-9 w-[170px]"
            value={fecha}
            onChange={(e) => setFecha(e.target.value)}
          />
        </div>
        <div className="flex-1 min-w-[220px]">
          <Label htmlFor="festivo-desc">Descripción</Label>
          <Input
            id="festivo-desc"
            className="h-9"
            maxLength={200}
            value={descripcion}
            onChange={(e) => setDescripcion(e.target.value)}
            placeholder="Feriado regional"
          />
        </div>
        <Button size="sm" onClick={onAgregar} disabled={crear.isPending}>
          <Plus className="size-3.5" />
          {crear.isPending ? "Guardando…" : "Agregar festivo"}
        </Button>
      </div>

      {isError ? (
        <p className="text-[13px] text-destructive">
          {error instanceof Error ? error.message : "Error al cargar"}
        </p>
      ) : isLoading ? (
        <p className="text-[13px] text-muted-foreground">Cargando…</p>
      ) : festivos.length === 0 ? (
        <p className="text-[13px] text-muted-foreground">Sin festivos registrados.</p>
      ) : (
        <ul className="divide-y rounded-md border">
          {festivos.map((f) => (
            <li key={f.id} className="flex items-center justify-between gap-3 px-3 py-2">
              <span className="font-mono text-[12.5px] w-[95px]">{fmtDate(f.fecha)}</span>
              <span className="flex-1 text-[13px]">{f.descripcion}</span>
              <Button
                size="sm"
                variant="ghost"
                aria-label={`Eliminar festivo ${f.fecha}`}
                onClick={() => onEliminar(f.id)}
                disabled={eliminar.isPending}
              >
                <Trash2 className="size-3.5" />
              </Button>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
