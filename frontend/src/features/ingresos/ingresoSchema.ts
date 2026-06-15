import { z } from "zod";
import { rutValido } from "@/lib/rut";

export const ingresoSchema = z.object({
  rut: z.string().refine(rutValido, "RUT inválido"),
  nombre: z.string().min(1, "Requerido"),
  sexo: z.enum(["F", "M", "otro"]),
  edad: z.coerce.number().int().min(1).max(130),
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
