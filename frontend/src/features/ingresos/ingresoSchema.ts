import { z } from "zod";
import { rutValido } from "@/lib/rut";

export const ingresoSchema = z.object({
  // Vacío pide el dato; el dígito verificador solo se revisa si hay algo escrito.
  rut: z
    .string()
    .min(1, "Requerido")
    .refine((v) => v === "" || rutValido(v), "RUT inválido"),
  nombre: z.string().min(1, "Requerido"),
  sexo: z.enum(["F", "M", "otro"]),
  // El input entrega texto: "" es "falta el dato", no un 0.
  edad: z.preprocess(
    (v) => (typeof v === "string" && v.trim() === "" ? undefined : v),
    z.coerce
      .number({ required_error: "Requerido", invalid_type_error: "Requerido" })
      .int("La edad debe ser un número entero")
      .min(1, "La edad debe estar entre 1 y 130")
      .max(130, "La edad debe estar entre 1 y 130"),
  ),
  region: z.string().min(1, "Requerido"),
  diagnostico: z.string().min(1, "Requerido"),
  tipo_derivacion: z.enum(["DIEP", "DIAT", "PAPT a flujo AT", "Reingreso FUMP", "Reingreso SUSESO", "Convenio U.Clinica", "Proyecto", "Particular", "PAPT"]),
  tipo_ingreso: z.enum(["consulta_espontanea", "convenio", "proyecto", "particular"]),
  modelo_tratamiento: z.string().min(1, "Requerido"),
  fecha_ingreso: z.string().min(1, "Requerido"),
  folio: z.string().optional(),
  es_reingreso: z.boolean().default(false),
});

export type IngresoForm = z.infer<typeof ingresoSchema>;
