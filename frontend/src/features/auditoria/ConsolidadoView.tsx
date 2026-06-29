/**
 * ConsolidadoView — vista de solo lectura de las 4 secciones del caso (§7.5.1–§7.5.4).
 */
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { fmtDate } from "@/lib/utils";
import type { CasoConsolidadoRead } from "./api";

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
        {label}
      </p>
      <p className="text-[13px]">{value ?? "—"}</p>
    </div>
  );
}

function d(v: string | null | undefined): string {
  return v ? fmtDate(v) : "—";
}

function Seccion({
  titulo,
  children,
}: {
  titulo: string;
  children: React.ReactNode;
}) {
  return (
    <Card className="p-5 space-y-3">
      <h3 className="text-[14px] font-semibold">{titulo}</h3>
      <div className="grid grid-cols-2 gap-x-6 gap-y-3">{children}</div>
    </Card>
  );
}

export function ConsolidadoView({ caso }: { caso: CasoConsolidadoRead }) {
  const { datos_caso, evaluaciones, controles, cierre } = caso;

  return (
    <div className="space-y-4">
      {/* §7.5.1 Datos del caso */}
      <Card className="p-5 space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Ingreso N° {caso.ingreso_id} · Folio {datos_caso.folio}
            </p>
            <h2 className="text-[16px] font-semibold">
              {datos_caso.nombre_completo}
            </h2>
            <p className="text-[12.5px] text-muted-foreground font-mono">
              {datos_caso.rut}
            </p>
          </div>
          <Badge variant="neutral">Solo lectura</Badge>
        </div>
        <div className="grid grid-cols-2 gap-x-6 gap-y-3">
          <Field label="N° siniestro" value={datos_caso.numero_siniestro} />
          <Field label="Región" value={datos_caso.region} />
          <Field label="Tipo denuncia" value={datos_caso.tipo_denuncia} />
          <Field label="Fecha denuncia" value={d(datos_caso.fecha_denuncia)} />
          <Field label="Fecha derivación" value={d(datos_caso.fecha_derivacion)} />
        </div>
      </Card>

      {/* §7.5.2 Evaluaciones */}
      <Seccion titulo="Seguimiento de evaluaciones">
        <Field label="Eval. médica" value={d(evaluaciones.fecha_eval_medica)} />
        <Field
          label="Eval. psicológica"
          value={d(evaluaciones.fecha_eval_psicologica)}
        />
        <Field
          label="Calificación RECA"
          value={d(evaluaciones.fecha_calificacion_reca)}
        />
        <Field
          label="Diagnóstico inicial"
          value={evaluaciones.diagnostico_inicial}
        />
        <Field
          label="Diagnóstico post-RECA"
          value={evaluaciones.diagnostico_post_reca}
        />
      </Seccion>

      {/* §7.5.3 Controles */}
      <Seccion titulo="Controles y tratamiento">
        <Field
          label="1ª consulta médica"
          value={d(controles.fecha_primera_consulta_medica)}
        />
        <Field
          label="1ª consulta psicológica"
          value={d(controles.fecha_primera_consulta_psicologica)}
        />
        <Field
          label="Reintegro parcial"
          value={
            controles.reintegro_parcial
              ? d(controles.fecha_reintegro_parcial) || "Sí"
              : "No"
          }
        />
        <Field
          label="Reintegro total"
          value={
            controles.reintegro_total
              ? d(controles.fecha_reintegro_total) || "Sí"
              : "No"
          }
        />
      </Seccion>

      {/* §7.5.4 Cierre */}
      <Seccion titulo="Cierre del caso">
        <Field
          label="Alta médica"
          value={cierre.alta_medica ? d(cierre.fecha_alta_medica) || "Sí" : "No"}
        />
        <Field
          label="Alta psicológica"
          value={
            cierre.alta_psicologica
              ? d(cierre.fecha_alta_psicologica) || "Sí"
              : "No"
          }
        />
        <Field
          label="Alta terapéutica"
          value={
            cierre.alta_terapeutica
              ? d(cierre.fecha_alta_terapeutica) || "Sí"
              : "No"
          }
        />
        <Field label="Estado general" value={cierre.estado_general} />
        <Field label="Observaciones" value={cierre.observaciones} />
      </Seccion>
    </div>
  );
}
