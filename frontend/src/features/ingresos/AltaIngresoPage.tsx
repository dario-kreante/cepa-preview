import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { ingresoSchema, type IngresoForm } from "./ingresoSchema";
import { useCrearIngreso } from "./hooks";
import type { IngresoCreate } from "./api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const TIPOS_DERIVACION = ["DIEP", "DIAT", "PAPT a flujo AT", "Reingreso FUMP", "Reingreso SUSESO", "Convenio U.Clinica", "Proyecto", "Particular", "PAPT"];
const TIPOS_INGRESO = ["consulta_espontanea", "convenio", "proyecto", "particular"];

export function AltaIngresoPage() {
  const nav = useNavigate();
  const crear = useCrearIngreso();
  const { register, handleSubmit, formState: { errors } } = useForm<IngresoForm>({
    resolver: zodResolver(ingresoSchema),
    defaultValues: { sexo: "F", es_reingreso: false },
  });

  async function onSubmit(values: IngresoForm) {
    try {
      const ingreso = await crear.mutateAsync(values as IngresoCreate);
      toast.success(`Ingreso creado · folio ${ingreso.folio}`);
      nav("/ingresos");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error");
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 max-w-xl">
      <h1 className="text-lg font-semibold">Nuevo ingreso</h1>
      {([
        ["rut", "RUT"], ["nombre", "Nombre"], ["edad", "Edad"], ["region", "Región"],
        ["diagnostico", "Diagnóstico"], ["modelo_tratamiento", "Modelo de tratamiento"],
      ] as const).map(([name, label]) => (
        <div key={name} className="space-y-1">
          <Label htmlFor={name}>{label}</Label>
          <Input id={name} {...register(name)} />
          {errors[name] && <p className="text-sm text-danger-600">{errors[name]?.message as string}</p>}
        </div>
      ))}
      <div className="space-y-1">
        <Label htmlFor="fecha_ingreso">Fecha de ingreso</Label>
        <Input id="fecha_ingreso" type="date" {...register("fecha_ingreso")} />
        {errors.fecha_ingreso && <p className="text-sm text-danger-600">{errors.fecha_ingreso.message}</p>}
      </div>
      <div className="space-y-1">
        <Label htmlFor="sexo">Sexo</Label>
        <select id="sexo" {...register("sexo")} className="w-full rounded-md border border-ink-300 px-3 py-2 text-sm">
          <option value="F">F</option><option value="M">M</option><option value="otro">Otro</option>
        </select>
      </div>
      <div className="space-y-1">
        <Label htmlFor="tipo_derivacion">Tipo de derivación</Label>
        <select id="tipo_derivacion" {...register("tipo_derivacion")} className="w-full rounded-md border border-ink-300 px-3 py-2 text-sm">
          {TIPOS_DERIVACION.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>
      <div className="space-y-1">
        <Label htmlFor="tipo_ingreso">Tipo de ingreso</Label>
        <select id="tipo_ingreso" {...register("tipo_ingreso")} className="w-full rounded-md border border-ink-300 px-3 py-2 text-sm">
          {TIPOS_INGRESO.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>
      <Button type="submit" disabled={crear.isPending}>{crear.isPending ? "Creando…" : "Crear ingreso"}</Button>
    </form>
  );
}
