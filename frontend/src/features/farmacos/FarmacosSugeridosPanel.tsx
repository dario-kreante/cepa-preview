/**
 * FarmacosSugeridosPanel — medicamentos leídos de las recetas de SALUTEM.
 *
 * SALUTEM guarda la receta como texto; el backend la estructura en medicamento,
 * dosis y frecuencia. Nada se registra solo: cada sugerencia abre el formulario de
 * siempre ("Agregar indicación" o "Nueva receta") precargado para revisarla.
 *
 * Sin registro farmacológico no se puede agregar nada: se muestran las sugerencias
 * y se pide crear el registro primero.
 */
import { useState } from "react";
import { AlertTriangle, CheckCircle2, Pill } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useFarmacosSugeridos } from "./hooks";
import { AgregarIndicacionDialog } from "./AgregarIndicacionDialog";
import { NuevaRecetaDialog } from "./NuevaRecetaDialog";
import { FRECUENCIA_LABELS } from "./indicacionSchema";
import type { IndicacionForm } from "./indicacionSchema";
import type { RecetaForm } from "./recetaSchema";
import type { FarmacoSugeridoRead, RegistroFarmacologicoRead } from "./api";

/** "2024-04-05" → "05/04/2024" */
function fechaCorta(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split("-");
  return y && m && d ? `${d}/${m}/${y}` : iso;
}

type Accion =
  | { tipo: "esquema"; valores: Partial<IndicacionForm> }
  | { tipo: "receta"; valores: Partial<RecetaForm> };

interface Props {
  ingresoId: number;
  registro: RegistroFarmacologicoRead | null | undefined;
  canWrite: boolean;
}

export function FarmacosSugeridosPanel({ ingresoId, registro, canWrite }: Props) {
  const { data: sugeridos = [] } = useFarmacosSugeridos(ingresoId);
  const [accion, setAccion] = useState<Accion | null>(null);

  if (sugeridos.length === 0) return null;

  const puedeAgregar = canWrite && registro != null;

  function cerrar(abierto: boolean) {
    if (!abierto) setAccion(null);
  }

  return (
    <section aria-labelledby="farmacos-sugeridos-titulo" className="space-y-2">
      <div className="px-0.5">
        <h2 id="farmacos-sugeridos-titulo" className="text-[14px] font-semibold">
          Fármacos recetados en SALUTEM
        </h2>
        <p className="text-[11.5px] text-muted-foreground">
          Leídos de las recetas de las atenciones. No se registran solos: revisa cada uno antes de
          agregarlo.
          {canWrite && registro == null && " Crea el registro farmacológico para poder agregarlos."}
        </p>
      </div>
      <ul className="space-y-2">
        {sugeridos.map((s: FarmacoSugeridoRead) => (
          <li key={`${s.medicamento}-${s.dosis}-${s.frecuencia}`}>
            <Card>
              <CardContent className="p-4 space-y-2">
                <div className="flex flex-wrap items-start gap-3">
                  <div className="size-9 rounded-md bg-muted grid place-items-center shrink-0">
                    <Pill className="size-4" />
                  </div>
                  <div className="flex-1 min-w-0 space-y-0.5">
                    <div className="text-[13px] font-semibold">
                      {s.medicamento} · {s.dosis} · {FRECUENCIA_LABELS[s.frecuencia]}
                    </div>
                    <div className="text-[11px] text-muted-foreground">
                      Atención del {fechaCorta(s.cita_fecha)}
                      {s.profesional ? ` · ${s.profesional}` : ""}
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    {s.en_esquema ? (
                      <Badge variant="success">
                        <CheckCircle2 className="size-3" /> En el esquema
                      </Badge>
                    ) : (
                      puedeAgregar && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            setAccion({
                              tipo: "esquema",
                              valores: {
                                medicamento: s.medicamento,
                                dosis: s.dosis,
                                frecuencia: s.frecuencia,
                              },
                            })
                          }
                        >
                          Agregar al esquema
                        </Button>
                      )
                    )}
                    {s.receta_registrada ? (
                      <Badge variant="success">
                        <CheckCircle2 className="size-3" /> Receta registrada
                      </Badge>
                    ) : (
                      puedeAgregar && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            setAccion({
                              tipo: "receta",
                              valores: {
                                fecha_emision: s.cita_fecha,
                                marca_medicamento: `${s.medicamento} ${s.dosis}`,
                              },
                            })
                          }
                        >
                          Registrar receta
                        </Button>
                      )
                    )}
                  </div>
                </div>
                <blockquote className="border-l-2 pl-3 text-[11.5px] text-muted-foreground italic">
                  {s.texto}
                </blockquote>
                {s.avisos.map((a) => (
                  <div
                    key={a}
                    className="flex items-start gap-1.5 rounded-md bg-amber-50 px-2 py-1 text-[11.5px] text-amber-900"
                  >
                    <AlertTriangle className="size-3.5 mt-0.5 shrink-0" />
                    {a}
                  </div>
                ))}
              </CardContent>
            </Card>
          </li>
        ))}
      </ul>
      {puedeAgregar && (
        <>
          <AgregarIndicacionDialog
            ingresoId={ingresoId}
            open={accion?.tipo === "esquema"}
            onOpenChange={cerrar}
            valoresIniciales={accion?.tipo === "esquema" ? accion.valores : undefined}
          />
          <NuevaRecetaDialog
            ingresoId={ingresoId}
            open={accion?.tipo === "receta"}
            onOpenChange={cerrar}
            valoresIniciales={accion?.tipo === "receta" ? accion.valores : undefined}
          />
        </>
      )}
    </section>
  );
}
