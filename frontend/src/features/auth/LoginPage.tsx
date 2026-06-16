import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { APP_NAME, APP_INITIAL, APP_SUBTITLE } from "@/lib/brand";

export function LoginPage() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [u, setU] = useState(""); const [p, setP] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null); setEnviando(true);
    try { await login(u, p); nav("/"); }
    catch { setError("Credenciales inválidas"); }
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
          <form onSubmit={onSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="u">Usuario</Label>
              <Input id="u" value={u} onChange={(e) => setU(e.target.value)} autoComplete="username" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="p">Contraseña</Label>
              <Input id="p" type="password" value={p} onChange={(e) => setP(e.target.value)} autoComplete="current-password" />
            </div>
            {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full" disabled={enviando}>
              {enviando ? "Ingresando…" : "Ingresar"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
