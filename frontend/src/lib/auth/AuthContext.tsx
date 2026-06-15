import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { jwtDecode } from "jwt-decode";
import { api } from "@/lib/apiClient";
import { tokenStore } from "@/lib/tokenStore";
import type { Rol } from "@/lib/rbac";

interface JwtClaims { sub: string; username: string; role: Rol; type: string; exp: number; }

interface AuthState {
  rol: Rol | null;
  username: string | null;
  cargando: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthCtx = createContext<AuthState | null>(null);

function rolDesdeToken(token: string | null): { rol: Rol | null; username: string | null } {
  if (!token) return { rol: null, username: null };
  try {
    const c = jwtDecode<JwtClaims>(token);
    return { rol: c.role, username: c.username };
  } catch {
    return { rol: null, username: null };
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [rol, setRol] = useState<Rol | null>(() => rolDesdeToken(tokenStore.getAccess()).rol);
  const [username, setUsername] = useState<string | null>(() => rolDesdeToken(tokenStore.getAccess()).username);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    let activo = true;
    (async () => {
      if (!tokenStore.getAccess() && tokenStore.getRefresh()) {
        const refresh = tokenStore.getRefresh()!;
        const { data } = await api.POST("/api/v1/auth/refresh", {
          body: { refresh_token: refresh },
          fetch: (...args: Parameters<typeof fetch>) => globalThis.fetch(...args),
        });
        if (activo && data?.access_token) {
          tokenStore.setAccess(data.access_token);
          const r = rolDesdeToken(data.access_token);
          setRol(r.rol); setUsername(r.username);
        } else if (activo) {
          tokenStore.clear();
        }
      }
      if (activo) setCargando(false);
    })();
    return () => { activo = false; };
  }, []);

  async function login(user: string, password: string) {
    const { data, error } = await api.POST("/api/v1/auth/login", {
      body: { username: user, password },
      fetch: (...args: Parameters<typeof fetch>) => globalThis.fetch(...args),
    });
    if (error || !data) throw new Error("Credenciales inválidas");
    tokenStore.setAccess(data.access_token);
    tokenStore.setRefresh(data.refresh_token);
    const r = rolDesdeToken(data.access_token);
    setRol(r.rol); setUsername(r.username);
  }

  function logout() {
    tokenStore.clear();
    setRol(null); setUsername(null);
  }

  const value = useMemo(() => ({ rol, username, cargando, login, logout }), [rol, username, cargando]);
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth fuera de AuthProvider");
  return ctx;
}
