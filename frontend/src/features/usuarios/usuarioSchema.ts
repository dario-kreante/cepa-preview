/**
 * Zod schemas para alta/edición de usuarios (CEPA-002).
 * En alta: username + password obligatorios. En edición: username fijo y la
 * contraseña es opcional (solo se envía si se quiere cambiar).
 */
import { z } from "zod";
import type { RolUsuario } from "./api";

export const ROL_VALUES = [
  "Coordinacion",
  "Administrativo",
  "Auditor",
] as const satisfies readonly RolUsuario[];

export const ROL_LABELS: Record<RolUsuario, string> = {
  Coordinacion: "Coordinación",
  Administrativo: "Administrativo",
  Auditor: "Auditor",
};

const emailOpcional = z
  .string()
  .trim()
  .email("Correo inválido")
  .or(z.literal(""))
  .optional();

export const usuarioCreateSchema = z.object({
  username: z
    .string()
    .trim()
    .min(3, "El usuario debe tener al menos 3 caracteres"),
  nombre: z.string().trim().min(1, "El nombre es requerido"),
  password: z
    .string()
    .min(8, "La contraseña debe tener al menos 8 caracteres"),
  rol: z.enum(ROL_VALUES, { required_error: "El rol es requerido" }),
  email: emailOpcional,
});

export const usuarioEditSchema = z.object({
  username: z.string(), // solo lectura en edición
  nombre: z.string().trim().min(1, "El nombre es requerido"),
  password: z
    .string()
    .min(8, "La contraseña debe tener al menos 8 caracteres")
    .or(z.literal(""))
    .optional(),
  rol: z.enum(ROL_VALUES),
  email: emailOpcional,
});

export type UsuarioCreateForm = z.infer<typeof usuarioCreateSchema>;
export type UsuarioEditForm = z.infer<typeof usuarioEditSchema>;
