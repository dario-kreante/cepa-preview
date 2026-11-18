import { useState } from "react";
import { Bell } from "lucide-react";
import { toast } from "sonner";
import { Card } from "@/components/ui/card";
import { tituloAlerta } from "@/components/shell/AlertsPanel";
import { obtenerContextoAlerta, type AlertaRead } from "./api";
import { useAlertas } from "./hooks";
import { alertasPendientesDeModulo, type ModuloConAlertas } from "./modulo";

interface Props {
  modulo: ModuloConAlertas;
  /** Abre el caso o la licencia de la alerta (con el paciente, si ya se conoce). */
  onAbrir: (alerta: AlertaRead, paciente: { id: number; nombre: string | null }) => void;
}

function fecha(iso: string | null | undefined, timeZone?: string): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("es-CL", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    timeZone,
  });
}

/**
 * Alertas pendientes del módulo, a la vista al entrar. La cantidad coincide con el número
 * del menú lateral (misma función: alertasPendientesDeModulo). Sin alertas no dibuja nada.
 */
export function AlertasPendientesModulo({ modulo, onAbrir }: Props) {
  const { data: alertas = [], isLoading, isError, refetch } = useAlertas();
  const [abriendo, setAbriendo] = useState<number | null>(null);
  const pendientes = alertasPendientesDeModulo(alertas, modulo);

  if (isLoading) {
    return (
      <p className="text-[13px] text-muted-foreground px-1" data-testid="alertas-modulo-cargando">
        Cargando alertas…
      </p>
    );
  }
  if (isError) {
    return (
      <div
        role="alert"
        className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 flex items-center justify-between gap-3"
      >
        <p className="text-[13px] text-destructive">No se pudieron cargar las alertas.</p>
        <button type="button" className="text-[12.5px] underline" onClick={() => refetch()}>
          Reintentar
        </button>
      </div>
    );
  }
  if (pendientes.length === 0) return null;

  async function abrir(a: AlertaRead) {
    if (a.paciente_id) {
      onAbrir(a, { id: a.paciente_id, nombre: a.paciente_nombre ?? null });
      return;
    }
    // Alertas sin paciente directo (p. ej. atención de SALUTEM): se resuelve al abrir.
    setAbriendo(a.id);
    try {
      const ctx = await obtenerContextoAlerta(a.id);
      if (ctx.paciente_id) {
        onAbrir(a, { id: ctx.paciente_id, nombre: ctx.paciente_nombre ?? null });
      } else {
        toast.error("No se encontró el paciente de esta alerta.");
      }
    } catch {
      toast.error("No se pudo abrir el paciente de la alerta.");
    } finally {
      setAbriendo(null);
    }
  }

  return (
    <Card className="overflow-hidden p-0" data-testid="alertas-pendientes-modulo">
      <div className="px-4 py-3 border-b flex items-center gap-2">
        <Bell className="size-3.5 text-destructive" />
        <h2 className="text-[13.5px] font-semibold">
          Alertas pendientes de revisión ({pendientes.length})
        </h2>
      </div>
      <ul className="divide-y">
        {pendientes.map((a) => {
          const titulo = tituloAlerta(a.tipo, a.caso_tipo);
          return (
            <li key={a.id}>
              <button
                type="button"
                onClick={() => abrir(a)}
                disabled={abriendo === a.id}
                aria-label={`Abrir alerta: ${titulo}`}
                className="w-full text-left px-4 py-3 grid grid-cols-[1fr_auto] gap-x-4 hover:bg-muted/40 transition-colors"
              >
                <span>
                  <span className="block text-[13px] font-semibold">
                    {a.paciente_nombre ?? `Caso #${a.caso_id}`}
                  </span>
                  <span className="block text-[12.5px] text-muted-foreground">{titulo}</span>
                </span>
                <span className="text-[12px] text-muted-foreground font-mono self-center">
                  Vence: {fecha(a.plazo_objetivo, "UTC")}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}
