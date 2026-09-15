import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/lib/auth/AuthContext";
import { ErrorDeConexion } from "@/lib/apiClient";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { APP_NAME, APP_INITIAL, APP_SUBTITLE } from "@/lib/brand";

const MENSAJE_SERVIDOR =
  "No se pudo contactar con el servidor. Reintenta en unos minutos.";

/**
 * Sale de la SPA hacia el backend, que decide el método habilitado en el entorno
 * (SAML o huemul) y redirige a UTalca. Es navegación del navegador, no fetch:
 * el flujo son redirecciones de ida y vuelta.
 */
function irASsoInstitucional() {
  window.location.href = `${import.meta.env.VITE_API_BASE_URL}/api/v1/auth/sso/login`;
}

/**
 * Mensajes de los fallos del SSO, que el backend informa devolviendo al login
 * con ?sso_error=... Sin esto el usuario acabaría viendo un JSON del backend.
 */
const MENSAJES_SSO: Record<string, string> = {
  no_configurado:
    "El acceso con cuenta UTalca todavía no está habilitado. Ingresa con tu usuario y contraseña.",
  autenticacion_fallida:
    "No pudimos validar tu cuenta institucional. Si el problema persiste, contacta a Coordinación.",
};

export function LoginPage() {
  const { login, errorSesion } = useAuth();
  const nav = useNavigate();
  const [params] = useSearchParams();
  const avisoSso = MENSAJES_SSO[params.get("sso_error") ?? ""];
  const [u, setU] = useState(""); const [p, setP] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  // Si llegamos aquí porque no se pudo restaurar la sesión con el servidor caído,
  // explicamos el motivo en vez de mostrar un formulario sin contexto.
  const mensaje = error ?? (errorSesion === "servidor" ? MENSAJE_SERVIDOR : null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null); setEnviando(true);
    try { await login(u, p); nav("/"); }
    catch (e) {
      setError(e instanceof ErrorDeConexion ? MENSAJE_SERVIDOR : "Credenciales inválidas");
    }
    finally { setEnviando(false); }
  }

  return (
    <div className="min-h-screen grid place-items-center bg-muted">
      <Card className="w-full max-w-sm shadow-md">
        <CardHeader className="items-center gap-2 pb-2">
          <div className="size-10 rounded-lg bg-primary text-primary-foreground flex items-center justify-center font-bold text-lg select-none">
            {APP_INITIAL}
          </div>
          <h1 className="text-xl font-semibold tracking-tight">{APP_NAME}</h1>
          <p className="text-sm text-muted-foreground">{APP_SUBTITLE}</p>
        </CardHeader>
        <CardContent>
          {avisoSso && (
            <p
              role="alert"
              className="mb-4 rounded-md bg-muted px-3 py-2 text-sm text-muted-foreground"
            >
              {avisoSso}
            </p>
          )}
          <form onSubmit={onSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="u">Usuario</Label>
              <Input id="u" value={u} onChange={(e) => setU(e.target.value)} autoComplete="username" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="p">Contraseña</Label>
              <Input id="p" type="password" value={p} onChange={(e) => setP(e.target.value)} autoComplete="current-password" />
            </div>
            {mensaje && <p role="alert" className="text-sm text-destructive">{mensaje}</p>}
            <Button type="submit" className="w-full" disabled={enviando}>
              {enviando ? "Ingresando…" : "Ingresar"}
            </Button>
          </form>

          <div className="relative my-5">
            <div className="absolute inset-0 flex items-center" aria-hidden="true">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="bg-card px-2 text-muted-foreground">o</span>
            </div>
          </div>

          <Button
            type="button"
            variant="outline"
            className="w-full"
            onClick={irASsoInstitucional}
          >
            Ingresar con tu cuenta UTalca
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
