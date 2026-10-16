import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { usePendientesFolio } from "./hooks";
import { DescartarBorradorDialog } from "./DescartarBorradorDialog";
import type { PacientePendienteRead } from "./api";

/** "2026-10-15" (o ISO con hora) → "15-10-2026"; sin dato, "—". */
function fechaDMA(valor: string | null): string {
  if (!valor) return "—";
  const [a, m, d] = valor.slice(0, 10).split("-");
  return a && m && d ? `${d}-${m}-${a}` : "—";
}

export function PendientesFolioPage() {
  const navigate = useNavigate();
  const { data = [], isLoading, isError } = usePendientesFolio();
  const [aDescartar, setADescartar] = useState<PacientePendienteRead | null>(null);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Pendientes de folio</h1>
        <p className="text-[13px] text-muted-foreground">
          Pacientes que llegaron desde SALUTEM y esperan su folio para completar el registro.
        </p>
      </div>

      <Card className="overflow-hidden">
        {isLoading ? (
          <p className="p-6 text-[13px] text-muted-foreground">Cargando…</p>
        ) : isError ? (
          <p className="p-6 text-[13px] text-destructive">
            No se pudieron cargar los pacientes pendientes de folio.
          </p>
        ) : data.length === 0 ? (
          <p className="p-6 text-[13px] text-muted-foreground">
            No hay pacientes pendientes de folio.
          </p>
        ) : (
          <table className="w-full text-[13px]">
            <thead className="bg-muted/50 text-muted-foreground">
              <tr>
                {["Paciente", "Identificación SALUTEM", "Primera atención", "Atenciones", "Especialidad", ""].map(
                  (h) => (
                    <th
                      key={h || "acciones"}
                      className="text-left px-4 py-3 font-semibold text-[11px] uppercase tracking-wider"
                    >
                      {h}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {data.map((p) => (
                <tr key={p.id} className="border-t border-border">
                  <td className="px-4 py-3 font-medium">{p.nombre}</td>
                  <td className="px-4 py-3">{p.rut ?? p.identificacion_salutem ?? "—"}</td>
                  <td className="px-4 py-3">{fechaDMA(p.primera_atencion)}</td>
                  <td className="px-4 py-3">{p.atenciones}</td>
                  <td className="px-4 py-3">
                    {p.especialidades.length > 0 ? p.especialidades.join(", ") : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-2">
                      <Button
                        size="sm"
                        onClick={() => navigate(`/ingresos/nuevo?paciente=${p.id}`)}
                      >
                        Completar registro
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setADescartar(p)}>
                        Descartar
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <DescartarBorradorDialog
        paciente={aDescartar}
        onOpenChange={(open) => {
          if (!open) setADescartar(null);
        }}
      />
    </div>
  );
}
