/**
 * UsuariosPage — gestión de usuarios y roles (CEPA-002). Solo Coordinación.
 * Lista usuarios con su rol/estado, permite crear, editar y activar/desactivar.
 * No se permite desactivar la propia cuenta (evita auto-bloqueo).
 */
import { useState } from "react";
import { toast } from "sonner";
import { Plus, Pencil, UserCheck, UserX, ShieldCheck } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { fmtDate } from "@/lib/utils";
import { useAuth } from "@/lib/auth/AuthContext";
import { type Rol } from "@/lib/rbac";
import {
  useActivarUsuario,
  useDesactivarUsuario,
  useUsuarios,
} from "./hooks";
import { UsuarioDialog } from "./UsuarioDialog";
import { ROL_LABELS } from "./usuarioSchema";
import type { RolUsuario, UsuarioRead } from "./api";

function rolVariant(rol: string): "info" | "warning" | "neutral" {
  if (rol === "Coordinacion") return "info";
  if (rol === "Auditor") return "warning";
  return "neutral";
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="text-left px-4 py-3 font-semibold text-[11px] uppercase tracking-wider text-muted-foreground">
      {children}
    </th>
  );
}

export function UsuariosPage() {
  const { rol, username } = useAuth();
  const { data: usuarios = [], isLoading, isError, error } = useUsuarios();
  const desactivar = useDesactivarUsuario();
  const activar = useActivarUsuario();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editando, setEditando] = useState<UsuarioRead | undefined>(undefined);

  // RBAC: solo Coordinación gestiona usuarios (CEPA-002 RN-4).
  if ((rol as Rol) !== "Coordinacion") {
    return (
      <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-16 text-center">
        <ShieldCheck className="mx-auto mb-3 size-8 text-muted-foreground/50" />
        <p className="text-[13.5px] text-muted-foreground">
          La gestión de usuarios está restringida al perfil Coordinación.
        </p>
      </div>
    );
  }

  function abrirNuevo() {
    setEditando(undefined);
    setDialogOpen(true);
  }
  function abrirEdicion(u: UsuarioRead) {
    setEditando(u);
    setDialogOpen(true);
  }

  async function toggleActivo(u: UsuarioRead) {
    try {
      if (u.activo) await desactivar.mutateAsync(u.id);
      else await activar.mutateAsync(u.id);
      toast.success(u.activo ? "Usuario desactivado" : "Usuario activado");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">Usuarios</h1>
          <p className="text-[13px] text-muted-foreground mt-1">
            Gestión de cuentas y roles · solo Coordinación
          </p>
        </div>
        <Button size="sm" onClick={abrirNuevo} data-testid="btn-nuevo-usuario">
          <Plus className="size-3.5" /> Nuevo usuario
        </Button>
      </div>

      {isError && (
        <p className="text-[13px] text-destructive px-1">
          {error instanceof Error ? error.message : "Error al cargar usuarios"}
        </p>
      )}

      {isLoading ? (
        <p className="text-[13px] text-muted-foreground px-1">Cargando…</p>
      ) : (
        <Card className="overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/30 border-b">
                  <Th>Usuario</Th>
                  <Th>Nombre</Th>
                  <Th>Rol</Th>
                  <Th>Correo</Th>
                  <Th>Estado</Th>
                  <Th>Creado</Th>
                  <Th> </Th>
                </tr>
              </thead>
              <tbody>
                {usuarios.map((u) => {
                  const esYo = u.username === username;
                  return (
                    <tr
                      key={u.id}
                      className="border-b"
                      data-testid={`row-usuario-${u.id}`}
                    >
                      <td className="px-4 py-3 font-mono text-[12.5px]">
                        {u.username}
                        {esYo && (
                          <span className="ml-1.5 text-[10.5px] text-muted-foreground">
                            (tú)
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-[13px]">{u.nombre}</td>
                      <td className="px-4 py-3">
                        <Badge variant={rolVariant(u.rol)}>
                          {ROL_LABELS[u.rol as RolUsuario] ?? u.rol}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-[12.5px] text-muted-foreground">
                        {u.email ?? "—"}
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={u.activo ? "success" : "neutral"}>
                          {u.activo ? "Activo" : "Inactivo"}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 font-mono text-[12px] text-muted-foreground">
                        {fmtDate(u.created_at)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 text-[11.5px] px-2"
                            onClick={() => abrirEdicion(u)}
                            data-testid={`btn-editar-${u.id}`}
                          >
                            <Pencil className="size-3 mr-1" /> Editar
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 text-[11.5px] px-2"
                            disabled={esYo || desactivar.isPending || activar.isPending}
                            title={
                              esYo
                                ? "No puedes desactivar tu propia cuenta"
                                : undefined
                            }
                            onClick={() => toggleActivo(u)}
                            data-testid={`btn-toggle-${u.id}`}
                          >
                            {u.activo ? (
                              <>
                                <UserX className="size-3 mr-1" /> Desactivar
                              </>
                            ) : (
                              <>
                                <UserCheck className="size-3 mr-1" /> Activar
                              </>
                            )}
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <UsuarioDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        usuario={editando}
      />
    </div>
  );
}
