/**
 * UsuarioDialog — alta / edición de un usuario (CEPA-002, solo Coordinación).
 * En edición: username fijo y contraseña opcional (vacía = no cambia).
 */
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  ROL_LABELS,
  ROL_VALUES,
  usuarioCreateSchema,
  usuarioEditSchema,
  type UsuarioCreateForm,
} from "./usuarioSchema";
import { useActualizarUsuario, useCrearUsuario } from "./hooks";
import type { UsuarioRead } from "./api";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Si se provee, el diálogo edita ese usuario; si no, crea uno nuevo. */
  usuario?: UsuarioRead;
}

const selectCls =
  "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-[13px] shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-ring";

const DEFAULTS: UsuarioCreateForm = {
  username: "",
  nombre: "",
  password: "",
  rol: "Administrativo",
  email: "",
};

export function UsuarioDialog({ open, onOpenChange, usuario }: Props) {
  const isEdit = !!usuario;
  const crear = useCrearUsuario();
  const actualizar = useActualizarUsuario();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<UsuarioCreateForm>({
    resolver: zodResolver(isEdit ? usuarioEditSchema : usuarioCreateSchema),
    defaultValues: DEFAULTS,
  });

  useEffect(() => {
    if (open && usuario) {
      reset({
        username: usuario.username,
        nombre: usuario.nombre,
        password: "",
        rol: usuario.rol as UsuarioCreateForm["rol"],
        email: usuario.email ?? "",
      });
    } else if (open) {
      reset(DEFAULTS);
    }
  }, [open, usuario, reset]);

  async function onSubmit(v: UsuarioCreateForm) {
    try {
      if (isEdit) {
        await actualizar.mutateAsync({
          id: usuario.id,
          body: {
            nombre: v.nombre,
            rol: v.rol,
            email: v.email || null,
            ...(v.password ? { password: v.password } : {}),
          },
        });
        toast.success("Usuario actualizado");
      } else {
        await crear.mutateAsync({
          username: v.username,
          nombre: v.nombre,
          password: v.password,
          rol: v.rol,
          email: v.email || null,
        });
        toast.success("Usuario creado");
      }
      onOpenChange(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error al guardar");
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Editar usuario" : "Nuevo usuario"}</DialogTitle>
          <p className="text-[12.5px] text-muted-foreground">
            {isEdit
              ? "Actualiza nombre, rol, correo o contraseña."
              : "Crea una cuenta de acceso al sistema."}
          </p>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-2">
          <div>
            <Label htmlFor="username">Usuario</Label>
            <Input
              id="username"
              placeholder="ej. jperez"
              disabled={isEdit}
              {...register("username")}
            />
            {errors.username && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.username.message}
              </p>
            )}
          </div>

          <div>
            <Label htmlFor="nombre">Nombre completo</Label>
            <Input id="nombre" placeholder="ej. Juana Pérez" {...register("nombre")} />
            {errors.nombre && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.nombre.message}
              </p>
            )}
          </div>

          <div>
            <Label htmlFor="rol">Rol</Label>
            <select id="rol" className={selectCls} {...register("rol")}>
              {ROL_VALUES.map((r) => (
                <option key={r} value={r}>
                  {ROL_LABELS[r]}
                </option>
              ))}
            </select>
          </div>

          <div>
            <Label htmlFor="email">Correo (opcional)</Label>
            <Input
              id="email"
              type="email"
              placeholder="para notificaciones de alerta"
              {...register("email")}
            />
            {errors.email && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.email.message}
              </p>
            )}
          </div>

          <div>
            <Label htmlFor="password">
              {isEdit ? "Nueva contraseña (opcional)" : "Contraseña"}
            </Label>
            <Input
              id="password"
              type="password"
              placeholder={isEdit ? "Dejar en blanco para no cambiar" : "Mín. 8 caracteres"}
              {...register("password")}
            />
            {errors.password && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.password.message}
              </p>
            )}
          </div>

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="ghost"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting
                ? "Guardando…"
                : isEdit
                  ? "Guardar cambios"
                  : "Crear usuario"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
