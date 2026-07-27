import { useEffect, useState } from "react";

/** Tras esta espera asumimos que el backend está arrancando en frío y lo avisamos. */
const MS_HASTA_AVISO = 6000;

/**
 * Pantalla de espera mientras se restaura la sesión. Si la espera se alarga
 * (el backend de staging se duerme y tarda ~50s en despertar) lo explica, para
 * que no se confunda con una pantalla colgada.
 */
export function PantallaCargando() {
  const [demorado, setDemorado] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setDemorado(true), MS_HASTA_AVISO);
    return () => clearTimeout(t);
  }, []);

  return (
    <div className="min-h-screen grid place-items-center p-6 text-center">
      <div className="space-y-2">
        <p className="text-muted-foreground">Cargando…</p>
        {demorado && (
          <p className="text-sm text-muted-foreground max-w-xs">
            El servidor puede tardar hasta un minuto en despertar. Seguimos intentando…
          </p>
        )}
      </div>
    </div>
  );
}
