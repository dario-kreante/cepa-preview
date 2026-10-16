import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { ingresoSchema, ingresoSinRutSchema, type IngresoForm } from "./ingresoSchema";
import { useCrearIngreso, usePaciente } from "./hooks";
import type { IngresoCreate, PacienteRead } from "./api";
import { usePendientesFolio } from "@/features/pacientes-borrador/hooks";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const TIPOS_DERIVACION = ["DIEP", "DIAT", "PAPT a flujo AT", "Reingreso FUMP", "Reingreso SUSESO", "Convenio U.Clinica", "Proyecto", "Particular", "PAPT"];
const TIPOS_INGRESO = ["consulta_espontanea", "convenio", "proyecto", "particular"];

/**
 * Valores iniciales. Con un borrador de SALUTEM se precarga lo que ya se sabe; lo que
 * falta queda vacío (no se inventa un sexo, una edad ni una región).
 */
function valoresIniciales(paciente?: PacienteRead): Partial<IngresoForm> {
  if (!paciente) return { sexo: "F", es_reingreso: false };
  return {
    rut: paciente.rut ?? "",
    nombre: paciente.nombre,
    sexo: (paciente.sexo ?? "") as IngresoForm["sexo"],
    edad: (paciente.edad != null ? String(paciente.edad) : "") as unknown as number,
    region: paciente.region ?? "",
    es_reingreso: false,
  };
}

function AltaIngresoForm({ paciente }: { paciente?: PacienteRead }) {
  const nav = useNavigate();
  const crear = useCrearIngreso();
  // Un borrador que no trae RUT se completa sin RUT; cualquier otro caso lo exige.
  const rutOpcional = !!paciente && !paciente.rut;
  // La identificación de SALUTEM del borrador sin RUT viene de la lista de pendientes.
  const { data: pendientes = [] } = usePendientesFolio(rutOpcional);
  const identificacionSalutem = rutOpcional
    ? pendientes.find((p) => p.id === paciente.id)?.identificacion_salutem
    : null;

  const { register, handleSubmit, formState: { errors } } = useForm<IngresoForm>({
    resolver: zodResolver(rutOpcional ? ingresoSinRutSchema : ingresoSchema),
    defaultValues: valoresIniciales(paciente),
  });

  async function onSubmit(values: IngresoForm) {
    try {
      const body = (paciente
        ? { ...values, paciente_id: paciente.id, rut: values.rut?.trim() || null }
        : values) as IngresoCreate;
      const ingreso = await crear.mutateAsync(body);
      toast.success(`Ingreso creado · folio ${ingreso.folio}`);
      nav("/ingresos");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error");
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 max-w-xl">
      <h1 className="text-lg font-semibold">
        {paciente ? "Completar registro" : "Nuevo ingreso"}
      </h1>
      {paciente && (
        <p className="text-[13px] text-muted-foreground">
          Este paciente viene de SALUTEM y le falta el folio para completar su registro.
          {rutOpcional && (
            <>
              {" "}No tiene RUT: el RUT es opcional
              {identificacionSalutem ? (
                <>
                  {" "}(identificación en SALUTEM:{" "}
                  <span className="font-mono">{identificacionSalutem}</span>)
                </>
              ) : null}
              .
            </>
          )}
        </p>
      )}
      {([
        ["rut", rutOpcional ? "RUT (opcional)" : "RUT"], ["nombre", "Nombre"], ["edad", "Edad"], ["region", "Región"],
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
          <option value="" disabled>Seleccione…</option>
          <option value="F">F</option><option value="M">M</option><option value="otro">Otro</option>
        </select>
        {errors.sexo && <p className="text-sm text-danger-600">{errors.sexo.message}</p>}
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

export function AltaIngresoPage() {
  const [params] = useSearchParams();
  const crudo = params.get("paciente");
  const pacienteId = crudo && /^\d+$/.test(crudo) ? Number(crudo) : null;
  const { data: paciente, isLoading, isError } = usePaciente(pacienteId);

  if (crudo && pacienteId === null)
    return <p className="text-[13px] text-destructive">El paciente indicado no es válido.</p>;
  if (pacienteId !== null && isLoading)
    return <p className="text-[13px] text-muted-foreground">Cargando paciente…</p>;
  if (pacienteId !== null && (isError || !paciente))
    return <p className="text-[13px] text-destructive">No se pudo cargar el paciente.</p>;

  if (paciente && paciente.estado_registro !== "pendiente_folio")
    return (
      <div className="space-y-2">
        <p className="text-[13px]">
          {paciente.estado_registro === "descartado"
            ? "Este paciente fue descartado."
            : "Este paciente ya tiene su registro completo."}
        </p>
        <Link to="/ingresos" className="text-[13px] underline">
          Ir a Ingresos
        </Link>
      </div>
    );

  return <AltaIngresoForm paciente={paciente} />;
}
