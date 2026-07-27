import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { jwtDecode } from "jwt-decode";
import { api, ErrorDeConexion } from "@/lib/apiClient";
import { tokenStore } from "@/lib/tokenStore";
import type { Rol } from "@/lib/rbac";

interface JwtClaims { sub: string; username: string; role: Rol; type: string; exp: number; }

/** Por qué no se pudo restaurar la sesión guardada. */
export type ErrorSesion = "servidor" | "sesion";

interface AuthState {
  rol: Rol | null;
  username: string | null;
  cargando: boolean;
  errorSesion: ErrorSesion | null;
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
  const [errorSesion, setErrorSesion] = useState<ErrorSesion | null>(null);

  useEffect(() => {
    let activo = true;
    (async () => {
      try {
        if (!tokenStore.getAccess() && tokenStore.getRefresh()) {
          const refresh = tokenStore.getRefresh()!;
          const { data } = await api.POST("/api/v1/auth/refresh", {
            body: { refresh_token: refresh },
          });
          if (!activo) return;
          if (data?.access_token) {
            tokenStore.setAccess(data.access_token);
            const r = rolDesdeToken(data.access_token);
            setRol(r.rol); setUsername(r.username);
          } else {
            // El servidor rechazó el refresh: la sesión ya no vale.
            tokenStore.clear();
            setErrorSesion("sesion");
          }
        }
      } catch (e) {
        // El servidor no contestó (caído, sin red o timeout). La sesión puede
        // seguir siendo válida, así que conservamos el refresh token y solo
        // informamos; lo que NO podemos hacer es quedarnos cargando para siempre.
        if (activo) setErrorSesion(e instanceof ErrorDeConexion ? "servidor" : "sesion");
      } finally {
        if (activo) setCargando(false);
      }
    })();
    return () => { activo = false; };
  }, []);

  async function login(user: string, password: string) {
    setErrorSesion(null);
    const { data, error } = await api.POST("/api/v1/auth/login", {
      body: { username: user, password },
    });
    if (error || !data) throw new Error("Credenciales inválidas");
    tokenStore.setAccess(data.access_token);
    tokenStore.setRefresh(data.refresh_token);
    const r = rolDesdeToken(data.access_token);
    setRol(r.rol); setUsername(r.username);
  }

  function logout() {
    tokenStore.clear();
    setRol(null); setUsername(null); setErrorSesion(null);
  }

  const value = useMemo(
    () => ({ rol, username, cargando, errorSesion, login, logout }),
    [rol, username, cargando, errorSesion],
  );
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth fuera de AuthProvider");
  return ctx;
}
