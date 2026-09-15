/**
 * EditarFichaDialog — edición de la ficha de ingreso (BUG-2608-01 / CEPA-010).
 *
 * RUT y folio se muestran pero no se editan: el RUT ancla la integración con
 * SALUTEM y el folio tiene reglas propias (PA-v5-01). Un guardado fallido nunca
 * es silencioso: el error queda visible y el formulario conserva lo escrito.
 */
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
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
import { useActualizarIngreso } from "./hooks";
import type { IngresoRead, IngresoUpdate, PacienteRead } from "./api";

const TIPOS_DERIVACION = [
  "DIEP",
  "DIAT",
  "PAPT a flujo AT",
  "Reingreso FUMP",
  "Reingreso SUSESO",
  "Convenio U.Clinica",
  "Proyecto",
  "Particular",
  "PAPT",
] as const;

const TIPOS_INGRESO = {
  consulta_espontanea: "Consulta espontánea",
  convenio: "Convenio",
  proyecto: "Proyecto",
  particular: "Particular",
} as const;

const edicionSchema = z.object({
  nombre: z.string().trim().min(1, "Requerido"),
  sexo: z.enum(["F", "M", "otro"]),
  edad: z.coerce.number().int().min(1, "Edad fuera de rango").max(130, "Edad fuera de rango"),
  region: z.string().trim().min(1, "Requerido"),
  comuna: z.string().optional(),
  telefono: z.string().optional(),
  correo: z.string().optional(),
  diagnostico: z.string().trim().min(1, "Requerido"),
  tipo_derivacion: z.enum(TIPOS_DERIVACION),
  tipo_ingreso: z.enum(["consulta_espontanea", "convenio", "proyecto", "particular"]),
  modelo_tratamiento: z.string().trim().min(1, "Requerido"),
  fecha_ingreso: z.string().min(1, "Requerido"),
  fecha_diep_diat: z.string().optional(),
  razon_social: z.string().optional(),
  numero_siniestro: z.string().optional(),
});

type EdicionForm = z.infer<typeof edicionSchema>;

function valoresIniciales(paciente: PacienteRead, ingreso: IngresoRead): EdicionForm {
  return {
    nombre: paciente.nombre,
    sexo: paciente.sexo as EdicionForm["sexo"],
    edad: paciente.edad,
    region: paciente.region,
    comuna: paciente.comuna ?? "",
    telefono: paciente.telefono ?? "",
    correo: paciente.correo ?? "",
    diagnostico: ingreso.diagnostico,
    tipo_derivacion: ingreso.tipo_derivacion,
    tipo_ingreso: ingreso.tipo_ingreso,
    modelo_tratamiento: ingreso.modelo_tratamiento,
    fecha_ingreso: ingreso.fecha_ingreso,
    fecha_diep_diat: ingreso.fecha_diep_diat ?? "",
    razon_social: ingreso.razon_social ?? "",
    numero_siniestro: ingreso.numero_siniestro ?? "",
  };
}

/** Los opcionales vacíos viajan como null para que el backend los limpie. */
function aCuerpo(v: EdicionForm): IngresoUpdate {
  const vacioANull = (s: string | undefined) => (s?.trim() ? s.trim() : null);
  return {
    nombre: v.nombre.trim(),
    sexo: v.sexo,
    edad: v.edad,
    region: v.region.trim(),
    comuna: vacioANull(v.comuna),
    telefono: vacioANull(v.telefono),
    correo: vacioANull(v.correo),
    diagnostico: v.diagnostico.trim(),
    tipo_derivacion: v.tipo_derivacion,
    tipo_ingreso: v.tipo_ingreso,
    modelo_tratamiento: v.modelo_tratamiento.trim(),
    fecha_ingreso: v.fecha_ingreso,
    fecha_diep_diat: vacioANull(v.fecha_diep_diat),
    razon_social: vacioANull(v.razon_social),
    numero_siniestro: vacioANull(v.numero_siniestro),
  };
}

const selectClass =
  "w-full h-9 rounded-md border bg-card px-3 text-[13px] focus:outline-none focus:ring-2 focus:ring-ring";

interface Props {
  paciente: PacienteRead;
  ingreso: IngresoRead;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function EditarFichaDialog({ paciente, ingreso, open, onOpenChange }: Props) {
  const actualizar = useActualizarIngreso(paciente.id);
  const [errorGuardado, setErrorGuardado] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<EdicionForm>({
    resolver: zodResolver(edicionSchema),
    defaultValues: valoresIniciales(paciente, ingreso),
  });

  // Al abrir, el formulario parte de los datos vigentes.
  useEffect(() => {
    if (open) reset(valoresIniciales(paciente, ingreso));
  }, [open, paciente, ingreso, reset]);

  // El aviso de un guardado fallido no sobrevive a cerrar el diálogo.
  function cambiarApertura(abierto: boolean) {
    if (!abierto) setErrorGuardado(null);
    onOpenChange(abierto);
  }

  async function onSubmit(values: EdicionForm) {
    setErrorGuardado(null);
    try {
      await actualizar.mutateAsync({ ingresoId: ingreso.id, body: aCuerpo(values) });
      toast.success("Ficha actualizada");
      cambiarApertura(false);
    } catch (err) {
      setErrorGuardado(
        err instanceof Error ? err.message : "No se pudo guardar la ficha. Intenta nuevamente.",
      );
    }
  }

  function campo(name: keyof EdicionForm, label: string, type = "text") {
    return (
      <div>
        <Label htmlFor={`editar-${name}`}>{label}</Label>
        <Input id={`editar-${name}`} type={type} {...register(name)} />
        {errors[name] && (
          <p className="text-[11.5px] text-destructive mt-1">{errors[name]?.message}</p>
        )}
      </div>
    );
  }

  return (
    <Dialog open={open} onOpenChange={cambiarApertura}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Editar ficha</DialogTitle>
          <p className="text-[12.5px] text-muted-foreground">
            RUT <span className="font-mono">{paciente.rut}</span> · Folio{" "}
            <span className="font-mono">{ingreso.folio}</span>
            <span className="block text-[11.5px]">
              El RUT y el folio no se modifican desde la ficha.
            </span>
          </p>
        </DialogHeader>

        <form noValidate onSubmit={handleSubmit(onSubmit)} className="space-y-5 py-2">
          <fieldset className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <legend className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-2">
              Datos del paciente
            </legend>
            {campo("nombre", "Nombre")}
            <div>
              <Label htmlFor="editar-sexo">Sexo</Label>
              <select id="editar-sexo" className={selectClass} {...register("sexo")}>
                <option value="F">F</option>
                <option value="M">M</option>
                <option value="otro">Otro</option>
              </select>
            </div>
            {campo("edad", "Edad", "number")}
            {campo("region", "Región")}
            {campo("comuna", "Comuna")}
            {campo("telefono", "Teléfono")}
            {/* Texto y no "email": la validación nativa rechaza correos ya guardados con tilde. */}
            {campo("correo", "Correo")}
          </fieldset>

          <fieldset className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <legend className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-2">
              Datos del ingreso
            </legend>
            {campo("fecha_ingreso", "Fecha de ingreso", "date")}
            {campo("fecha_diep_diat", "Fecha DIEP/DIAT", "date")}
            <div>
              <Label htmlFor="editar-tipo_derivacion">Tipo de derivación</Label>
              <select
                id="editar-tipo_derivacion"
                className={selectClass}
                {...register("tipo_derivacion")}
              >
                {TIPOS_DERIVACION.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label htmlFor="editar-tipo_ingreso">Tipo de ingreso</Label>
              <select id="editar-tipo_ingreso" className={selectClass} {...register("tipo_ingreso")}>
                {Object.entries(TIPOS_INGRESO).map(([valor, label]) => (
                  <option key={valor} value={valor}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            <div className="sm:col-span-2">{campo("diagnostico", "Diagnóstico")}</div>
            {campo("modelo_tratamiento", "Modelo de tratamiento")}
            {campo("razon_social", "Razón social")}
            {campo("numero_siniestro", "N.º de siniestro")}
          </fieldset>

          {errorGuardado && (
            <div
              role="alert"
              className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-[12.5px] text-destructive"
            >
              No se pudo guardar la ficha: {errorGuardado}
            </div>
          )}

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="ghost"
              onClick={() => cambiarApertura(false)}
              disabled={isSubmitting}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Guardando…" : "Guardar cambios"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
