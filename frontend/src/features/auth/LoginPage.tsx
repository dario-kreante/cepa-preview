import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card } from "@/components/ui/card";

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
    <div className="min-h-screen grid place-items-center bg-ink-100">
      <Card className="w-full max-w-sm p-6 space-y-4">
        <h1 className="text-xl font-semibold text-brand-700">Sistema CEPA</h1>
        <form onSubmit={onSubmit} className="space-y-3">
          <div className="space-y-1">
            <Label htmlFor="u">Usuario</Label>
            <Input id="u" value={u} onChange={(e) => setU(e.target.value)} autoComplete="username" />
          </div>
          <div className="space-y-1">
            <Label htmlFor="p">Contraseña</Label>
            <Input id="p" type="password" value={p} onChange={(e) => setP(e.target.value)} autoComplete="current-password" />
          </div>
          {error && <p role="alert" className="text-sm text-danger-600">{error}</p>}
          <Button type="submit" className="w-full" disabled={enviando}>
            {enviando ? "Ingresando…" : "Ingresar"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
