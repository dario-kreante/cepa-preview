/**
 * ConveniosPage — catálogo de convenios de la Unidad Clínica.
 *
 * El catálogo se refleja desde SALUTEM («Actualizar desde SALUTEM» y el modo frío). Aquí el CEPA
 * decide cuáles son visibles en la ficha de ingreso y puede agregar convenios propios (origen
 * SIGE); los de SALUTEM no se renombran. Nunca se borra un convenio.
 */
import { useState } from "react";
import { toast } from "sonner";
import { DownloadCloud, Pencil, Plus, ShieldCheck } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useAuth } from "@/lib/auth/AuthContext";
import { puedeEscribir, type Rol } from "@/lib/rbac";
import {
  useActualizarConvenio,
  useActualizarDesdeSalutem,
  useConvenios,
  useCrearConvenio,
} from "./hooks";
import type { ActualizacionConvenios, ConvenioRead } from "./api";

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="text-left px-4 py-3 font-semibold text-[11px] uppercase tracking-wider text-muted-foreground">
      {children}
    </th>
  );
}

/** «23-11-2026 07:10» en hora local; «—» si no hay fecha. */
function fmtFechaHora(iso: string | null): string {
  if (!iso) return "—";
  const conZona = /(Z|[+-]\d{2}:?\d{2})$/.test(iso) ? iso : `${iso}Z`;
  const d = new Date(conZona);
  if (Number.isNaN(d.getTime())) return "—";
  const p = (n: number) => String(n).padStart(2, "0");
  return `${p(d.getDate())}-${p(d.getMonth() + 1)}-${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

function ultimaActualizacion(convenios: ConvenioRead[]): string | null {
  let mejor: string | null = null;
  let mejorT = -Infinity;
  for (const c of convenios) {
    if (!c.sincronizado_en) continue;
    const conZona = /(Z|[+-]\d{2}:?\d{2})$/.test(c.sincronizado_en)
      ? c.sincronizado_en
      : `${c.sincronizado_en}Z`;
    const t = new Date(conZona).getTime();
    if (!Number.isNaN(t) && t > mejorT) {
      mejorT = t;
      mejor = c.sincronizado_en;
    }
  }
  return mejor;
}

function resumenActualizacion(r: ActualizacionConvenios): string {
  const nuevos = r.creados === 1 ? "1 nuevo" : `${r.creados} nuevos`;
  const act = r.actualizados === 1 ? "1 actualizado" : `${r.actualizados} actualizados`;
  const des = r.desactivados === 1 ? "1 desactivado" : `${r.desactivados} desactivados`;
  return `${nuevos}, ${act}, ${des}`;
}

function ConvenioForm({
  convenio,
  onDone,
}: {
  convenio?: ConvenioRead;
  onDone: () => void;
}) {
  const crear = useCrearConvenio();
  const actualizar = useActualizarConvenio();
  const [nombre, setNombre] = useState(convenio?.nombre ?? "");
  const [errorNombre, setErrorNombre] = useState<string | null>(null);

  async function guardar(e: React.FormEvent) {
    e.preventDefault();
    if (!nombre.trim()) {
      setErrorNombre("El nombre es obligatorio");
      return;
    }
    try {
      if (convenio)
        await actualizar.mutateAsync({ id: convenio.id, body: { nombre: nombre.trim() } });
      else await crear.mutateAsync({ nombre: nombre.trim() });
      toast.success(convenio ? "Convenio actualizado" : "Convenio creado");
      onDone();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error al guardar");
    }
  }

  const pendiente = crear.isPending || actualizar.isPending;

  return (
    <form onSubmit={guardar} className="space-y-4" noValidate>
      <div>
        <Label htmlFor="convenio-nombre" className="text-[12px]">
          Nombre
        </Label>
        <Input
          id="convenio-nombre"
          value={nombre}
          maxLength={120}
          onChange={(e) => {
            setNombre(e.target.value);
            setErrorNombre(null);
          }}
          className="mt-1 h-9 text-[13px]"
          data-testid="input-convenio-nombre"
        />
        {errorNombre && <p className="text-[12px] text-destructive mt-1">{errorNombre}</p>}
      </div>
      {!convenio && (
        <p className="text-[12px] text-muted-foreground rounded-md border bg-muted/30 px-3 py-2">
          Este convenio solo existirá en SIGE: conviene crearlo también en SALUTEM. Cuando
          exista allá con el mismo nombre, la próxima actualización lo reconocerá.
        </p>
      )}
      <DialogFooter>
        <Button type="button" variant="outline" size="sm" onClick={onDone}>
          Cancelar
        </Button>
        <Button type="submit" size="sm" disabled={pendiente} data-testid="btn-guardar-convenio">
          {pendiente ? "Guardando…" : "Guardar"}
        </Button>
      </DialogFooter>
    </form>
  );
}

function ConvenioDialog({
  open,
  onOpenChange,
  convenio,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  convenio?: ConvenioRead;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[440px]">
        <DialogHeader>
          <DialogTitle>{convenio ? "Renombrar convenio" : "Agregar convenio"}</DialogTitle>
        </DialogHeader>
        <ConvenioForm
          key={convenio?.id ?? "nuevo"}
          convenio={convenio}
          onDone={() => onOpenChange(false)}
        />
      </DialogContent>
    </Dialog>
  );
}

export function ConveniosPage() {
  const { rol } = useAuth();
  const canWrite = puedeEscribir(rol as Rol);
  const { data: convenios = [], isLoading, isError, error } = useConvenios();
  const actualizar = useActualizarConvenio();
  const sincronizar = useActualizarDesdeSalutem();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editando, setEditando] = useState<ConvenioRead | undefined>(undefined);
  const [resultado, setResultado] = useState<ActualizacionConvenios | null>(null);

  if (!canWrite) {
    return (
      <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-16 text-center">
        <ShieldCheck className="mx-auto mb-3 size-8 text-muted-foreground/50" />
        <p className="text-[13.5px] text-muted-foreground">
          El catálogo de convenios lo gestionan Coordinación y Administrativo.
        </p>
      </div>
    );
  }

  function abrir(c?: ConvenioRead) {
    setEditando(c);
    setDialogOpen(true);
  }

  async function cambiarVisible(c: ConvenioRead, visible: boolean) {
    try {
      await actualizar.mutateAsync({ id: c.id, body: { visible } });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    }
  }

  async function onActualizar() {
    try {
      const r = await sincronizar.mutateAsync();
      setResultado(r);
      if (r.errores.length > 0) toast.warning(`Actualización con errores: ${resumenActualizacion(r)}`);
      else toast.success(`Actualizado desde SALUTEM: ${resumenActualizacion(r)}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error al actualizar");
    }
  }

  const ultima = ultimaActualizacion(convenios);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">Convenios</h1>
          <p className="text-[13px] text-muted-foreground mt-1" data-testid="ultima-actualizacion">
            Última actualización: {fmtFechaHora(ultima)}
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={onActualizar}
            disabled={sincronizar.isPending}
            data-testid="btn-actualizar-salutem"
          >
            <DownloadCloud className="size-3.5" />
            {sincronizar.isPending ? "Actualizando…" : "Actualizar desde SALUTEM"}
          </Button>
          <Button size="sm" onClick={() => abrir()} data-testid="btn-agregar-convenio">
            <Plus className="size-3.5" /> Agregar
          </Button>
        </div>
      </div>

      {resultado && resultado.errores.length > 0 && (
        <Card className="p-4 space-y-1" data-testid="errores-actualizacion">
          <p className="text-[12.5px] font-medium text-destructive">
            {resultado.errores.length} error(es) durante la actualización
          </p>
          <ul className="list-disc pl-5 text-[12px] text-destructive space-y-0.5">
            {resultado.errores.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </Card>
      )}

      {isError && (
        <p className="text-[13px] text-destructive px-1">
          {error instanceof Error ? error.message : "Error al cargar convenios"}
        </p>
      )}

      {isLoading ? (
        <p className="text-[13px] text-muted-foreground px-1">Cargando…</p>
      ) : convenios.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-12 text-center">
          <p className="text-[13.5px] text-muted-foreground">
            Aún no hay convenios. Actualiza desde SALUTEM o agrega uno.
          </p>
        </div>
      ) : (
        <Card className="overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/30 border-b">
                  <Th>Nombre</Th>
                  <Th>Origen</Th>
                  <Th>En SALUTEM</Th>
                  <Th>Visible</Th>
                  <Th> </Th>
                </tr>
              </thead>
              <tbody>
                {convenios.map((c) => {
                  const deSalutem = c.salutem_id !== null;
                  return (
                    <tr key={c.id} className="border-b" data-testid={`row-convenio-${c.id}`}>
                      <td className="px-4 py-3 text-[13px]">{c.nombre}</td>
                      <td className="px-4 py-3">
                        <Badge variant={deSalutem ? "info" : "neutral"}>
                          {deSalutem ? "SALUTEM" : "SIGE"}
                        </Badge>
                      </td>
                      <td className="px-4 py-3">
                        {deSalutem ? (
                          <Badge variant={c.activo_salutem ? "success" : "neutral"}>
                            {c.activo_salutem ? "Activo" : "Inactivo"}
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <Checkbox
                          checked={c.visible}
                          disabled={actualizar.isPending}
                          onCheckedChange={(v) => cambiarVisible(c, v === true)}
                          aria-label={`Visible: ${c.nombre}`}
                        />
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end">
                          {!deSalutem && (
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-7 text-[11.5px] px-2"
                              onClick={() => abrir(c)}
                              data-testid={`btn-renombrar-convenio-${c.id}`}
                            >
                              <Pencil className="size-3 mr-1" /> Renombrar
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <ConvenioDialog open={dialogOpen} onOpenChange={setDialogOpen} convenio={editando} />
    </div>
  );
}
