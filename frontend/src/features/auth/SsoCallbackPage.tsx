import { useEffect, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { useAuth } from "@/lib/auth/AuthContext";

/**
 * Aterrizaje del login SSO institucional.
 *
 * El IdP de UTalca hace POST de la aserción al backend, que la valida y redirige
 * aquí con un código de un solo uso. Este componente lo canjea por la sesión.
 *
 * Los tokens nunca viajan en la URL: lo que llega es un código efímero que el
 * backend invalida al primer canje.
 */
export function SsoCallbackPage() {
  const [params] = useSearchParams();
  const nav = useNavigate();
  const { canjearCodigoSso } = useAuth();
  // En StrictMode el efecto corre dos veces; el código es de un solo uso, así que
  // el segundo intento fallaría y mandaría al usuario al login sin motivo.
  const yaCanjeado = useRef(false);

  const code = params.get("code");
  const destino = params.get("redirect") || "/";

  useEffect(() => {
    if (yaCanjeado.current) return;
    yaCanjeado.current = true;

    if (!code) {
      nav("/login", { replace: true });
      return;
    }

    canjearCodigoSso(code)
      .then(() => nav(destino, { replace: true }))
      .catch(() => nav("/login", { replace: true }));
  }, [code, destino, canjearCodigoSso, nav]);

  return (
    <div className="min-h-screen grid place-items-center bg-muted">
      <p className="text-sm text-muted-foreground" role="status">
        Validando tu sesión institucional…
      </p>
    </div>
  );
}
