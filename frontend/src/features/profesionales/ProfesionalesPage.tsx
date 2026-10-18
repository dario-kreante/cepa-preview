/**
 * ProfesionalesPage — catálogo de profesionales para el agendamiento.
 *
 * La Agenda elige al profesional desde esta lista (antes se escribía un ID a mano). Se siembra
 * con los médicos tratantes de los controles de SALUTEM; "Importar desde SALUTEM" trae los que
 * hayan aparecido después. Desactivar lo saca del selector de Agenda sin borrar su historial.
 */
import { useState } from "react";
import { toast } from "sonner";
import { Link } from "react-router-dom";
import { DownloadCloud, Pencil, Plus, ShieldCheck, UserCheck, UserX } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { fmtDate, fmtRelativo } from "@/lib/utils";
import { useAuth } from "@/lib/auth/AuthContext";
import { puedeEscribir, type Rol } from "@/lib/rbac";
import {
  useActividadProfesional,
  useActualizarProfesional,
  useCrearProfesional,
  useImportarDesdeSalutem,
  useProfesionales,
} from "./hooks";
import type { ImportacionSalutem, ProfesionalRead } from "./api";

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="text-left px-4 py-3 font-semibold text-[11px] uppercase tracking-wider text-muted-foreground">
      {children}
    </th>
  );
}

function ProfesionalDialog({
  open,
  onOpenChange,
  profesional,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  profesional?: ProfesionalRead;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[440px]">
        <DialogHeader>
          <DialogTitle>{profesional ? "Editar profesional" : "Nuevo profesional"}</DialogTitle>
        </DialogHeader>
        {/* El contenido se monta al abrir: el formulario parte de los datos del profesional. */}
        <ProfesionalForm
          key={profesional?.id ?? "nuevo"}
          profesional={profesional}
          onDone={() => onOpenChange(false)}
        />
      </DialogContent>
    </Dialog>
  );
}

function ProfesionalForm({
  profesional,
  onDone,
}: {
  profesional?: ProfesionalRead;
  onDone: () => void;
}) {
  const crear = useCrearProfesional();
  const actualizar = useActualizarProfesional();
  const [nombre, setNombre] = useState(profesional?.nombre ?? "");
  const [especialidad, setEspecialidad] = useState(profesional?.especialidad ?? "");
  const [errorNombre, setErrorNombre] = useState<string | null>(null);

  async function guardar(e: React.FormEvent) {
    e.preventDefault();
    if (!nombre.trim()) {
      setErrorNombre("El nombre es obligatorio");
      return;
    }
    const body = { nombre: nombre.trim(), especialidad: especialidad.trim() || null };
    try {
      if (profesional) await actualizar.mutateAsync({ id: profesional.id, body });
      else await crear.mutateAsync(body);
      toast.success(profesional ? "Profesional actualizado" : "Profesional creado");
      onDone();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error al guardar");
    }
  }

  const pendiente = crear.isPending || actualizar.isPending;

  return (
    <form onSubmit={guardar} className="space-y-4" noValidate>
      <div>
        <Label htmlFor="prof-nombre" className="text-[12px]">
          Nombre
        </Label>
        <Input
          id="prof-nombre"
          value={nombre}
          maxLength={160}
          onChange={(e) => {
            setNombre(e.target.value);
            setErrorNombre(null);
          }}
          className="mt-1 h-9 text-[13px]"
          data-testid="input-prof-nombre"
        />
        {profesional?.origen === "SALUTEM" && (
          <p className="text-[11.5px] text-muted-foreground mt-1">
            Viene de SALUTEM: si cambias el nombre, la próxima importación lo volverá a traer
            con el nombre original.
          </p>
        )}
        {errorNombre && <p className="text-[12px] text-destructive mt-1">{errorNombre}</p>}
      </div>
      <div>
        <Label htmlFor="prof-especialidad" className="text-[12px]">
          Especialidad (opcional)
        </Label>
        <Input
          id="prof-especialidad"
          value={especialidad}
          maxLength={80}
          onChange={(e) => setEspecialidad(e.target.value)}
          placeholder="Ej.: Psiquiatría"
          className="mt-1 h-9 text-[13px]"
        />
      </div>
      <DialogFooter>
        <Button type="button" variant="outline" size="sm" onClick={onDone}>
          Cancelar
        </Button>
        <Button type="submit" size="sm" disabled={pendiente} data-testid="btn-guardar-prof">
          {pendiente ? "Guardando…" : "Guardar"}
        </Button>
      </DialogFooter>
    </form>
  );
}

function Dato({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-md border bg-muted/20 px-3 py-2">
      <p className="text-[10.5px] uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="text-[15px] font-semibold mt-0.5">{value}</p>
    </div>
  );
}

function DetalleProfesionalDialog({
  profesional,
  onClose,
}: {
  profesional: ProfesionalRead | null;
  onClose: () => void;
}) {
  const { data, isLoading, isError } = useActividadProfesional(profesional?.id ?? null);
  return (
    <Dialog open={profesional !== null} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-[640px] max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{profesional?.nombre}</DialogTitle>
          <p className="text-[12.5px] text-muted-foreground">
            {profesional?.especialidades?.length
              ? profesional.especialidades.join(" · ")
              : (profesional?.especialidad ?? "Sin especialidad registrada")}
            {profesional?.sucursales?.length
              ? ` — ${profesional.sucursales.join(", ")}`
              : ""}
          </p>
        </DialogHeader>
        {isLoading && <p className="text-[13px] text-muted-foreground">Cargando actividad…</p>}
        {isError && (
          <p className="text-[13px] text-destructive">No se pudo cargar la actividad.</p>
        )}
        {data && (
          <div className="space-y-4" data-testid="detalle-actividad">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <Dato label="Atenciones" value={data.total_atenciones} />
              <Dato label="Controles" value={data.total_controles} />
              <Dato label="Pacientes" value={data.pacientes_distintos} />
              <Dato
                label="Última atención"
                value={data.ultima_atencion ? fmtDate(data.ultima_atencion) : "—"}
              />
            </div>
            {data.primera_atencion && (
              <p className="text-[12px] text-muted-foreground">
                Primera atención registrada: {fmtDate(data.primera_atencion)}
              </p>
            )}
            {data.atenciones_por_especialidad.length > 0 && (
              <div>
                <h3 className="text-[12.5px] font-semibold mb-2">Atenciones por especialidad</h3>
                <div className="flex flex-wrap gap-2">
                  {data.atenciones_por_especialidad.map((a) => (
                    <Badge key={a.especialidad} variant="info">
                      {a.especialidad} · {a.total}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
            <div>
              <h3 className="text-[12.5px] font-semibold mb-2">Últimas atenciones</h3>
              {data.ultimas_atenciones.length === 0 ? (
                <p className="text-[13px] text-muted-foreground">
                  Aún no hay atenciones vinculadas a este profesional.
                </p>
              ) : (
                <ul className="divide-y rounded-md border">
                  {data.ultimas_atenciones.map((a) => (
                    <li
                      key={a.ficha_id}
                      className="flex items-center justify-between gap-3 px-3 py-2 text-[12.5px]"
                    >
                      <span className="text-muted-foreground w-[84px] shrink-0">
                        {a.fecha ? fmtDate(a.fecha) : "—"}
                      </span>
                      <span className="flex-1 truncate">
                        <Link
                          to={`/ingresos?paciente=${a.paciente_id}`}
                          className="font-medium underline-offset-2 hover:underline"
                          data-testid={`link-atencion-${a.ficha_id}`}
                        >
                          {a.paciente}
                        </Link>
                        <span className="text-muted-foreground"> · folio {a.folio}</span>
                      </span>
                      <span className="text-muted-foreground">{a.especialidad ?? "—"}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

function ResultadoImportacion({
  resultado,
  onCerrar,
}: {
  resultado: ImportacionSalutem;
  onCerrar: () => void;
}) {
  return (
    <Card className="p-4 space-y-2" data-testid="resultado-importacion">
      <div className="flex items-start justify-between gap-3">
        <p className="text-[13px]">
          <span className="font-semibold">Importación desde SALUTEM:</span>{" "}
          {resultado.creados} creados · {resultado.actualizados} actualizados ·{" "}
          {resultado.adoptados} adoptados · {resultado.vinculados} vinculados
        </p>
        <Button size="sm" variant="ghost" className="h-6 px-2 text-[11.5px]" onClick={onCerrar}>
          Cerrar
        </Button>
      </div>
      {resultado.errores.length > 0 && (
        <div>
          <p className="text-[12.5px] font-medium text-destructive">
            {resultado.errores.length} error(es) durante la importación
          </p>
          <ul className="list-disc pl-5 text-[12px] text-destructive mt-1 space-y-0.5">
            {resultado.errores.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}

export function ProfesionalesPage() {
  const { rol } = useAuth();
  const canWrite = puedeEscribir(rol as Rol);
  const { data: profesionales = [], isLoading, isError, error } = useProfesionales();
  const actualizar = useActualizarProfesional();
  const importar = useImportarDesdeSalutem();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editando, setEditando] = useState<ProfesionalRead | undefined>(undefined);
  const [detalle, setDetalle] = useState<ProfesionalRead | null>(null);
  const [resultado, setResultado] = useState<ImportacionSalutem | null>(null);

  if (!canWrite) {
    return (
      <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-16 text-center">
        <ShieldCheck className="mx-auto mb-3 size-8 text-muted-foreground/50" />
        <p className="text-[13.5px] text-muted-foreground">
          El catálogo de profesionales lo gestionan Coordinación y Administrativo.
        </p>
      </div>
    );
  }

  function abrir(p?: ProfesionalRead) {
    setEditando(p);
    setDialogOpen(true);
  }

  async function toggleActivo(p: ProfesionalRead) {
    try {
      await actualizar.mutateAsync({ id: p.id, body: { activo: !p.activo } });
      toast.success(p.activo ? "Profesional desactivado" : "Profesional activado");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    }
  }

  async function onImportar() {
    try {
      const r = await importar.mutateAsync();
      setResultado(r);
      const cambios = r.creados + r.actualizados + r.adoptados + r.vinculados;
      if (r.errores.length > 0) toast.warning("Importación terminada con errores");
      else
        toast.success(
          cambios === 0
            ? "Todo al día: no hay cambios en SALUTEM"
            : "Importación desde SALUTEM completada",
        );
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error al importar");
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">Profesionales</h1>
          <p className="text-[13px] text-muted-foreground mt-1">
            Catálogo que usa el agendamiento · los inactivos no aparecen en la Agenda
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={onImportar}
            disabled={importar.isPending}
            data-testid="btn-importar-salutem"
          >
            <DownloadCloud className="size-3.5" />
            {importar.isPending ? "Importando…" : "Importar desde SALUTEM"}
          </Button>
          <Button size="sm" onClick={() => abrir()} data-testid="btn-nuevo-prof">
            <Plus className="size-3.5" /> Nuevo profesional
          </Button>
        </div>
      </div>

      {resultado && (
        <ResultadoImportacion resultado={resultado} onCerrar={() => setResultado(null)} />
      )}

      {isError && (
        <p className="text-[13px] text-destructive px-1">
          {error instanceof Error ? error.message : "Error al cargar profesionales"}
        </p>
      )}

      {isLoading ? (
        <p className="text-[13px] text-muted-foreground px-1">Cargando…</p>
      ) : profesionales.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-12 text-center">
          <p className="text-[13.5px] text-muted-foreground">
            Aún no hay profesionales. Impórtalos desde SALUTEM o crea uno nuevo.
          </p>
        </div>
      ) : (
        <Card className="overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/30 border-b">
                  <Th>Nombre</Th>
                  <Th>Especialidades</Th>
                  <Th>Origen</Th>
                  <Th>Última atención</Th>
                  <Th>Sincronizado</Th>
                  <Th>Estado</Th>
                  <Th> </Th>
                </tr>
              </thead>
              <tbody>
                {profesionales.map((p) => (
                  <tr
                    key={p.id}
                    className="border-b cursor-pointer hover:bg-muted/30"
                    onClick={() => setDetalle(p)}
                    data-testid={`row-prof-${p.id}`}
                  >
                    <td className="px-4 py-3 text-[13px]">{p.nombre}</td>
                    <td className="px-4 py-3 text-[12.5px] text-muted-foreground">
                      {p.especialidades?.length
                        ? p.especialidades.join(", ")
                        : (p.especialidad ?? "—")}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={p.origen === "SALUTEM" ? "info" : "neutral"}>
                        {p.origen}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-[12.5px] text-muted-foreground">
                      {p.ultima_atencion ? fmtDate(p.ultima_atencion) : "—"}
                    </td>
                    <td className="px-4 py-3 text-[12.5px] text-muted-foreground">
                      {fmtRelativo(p.sincronizado_en)}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={p.activo ? "success" : "neutral"}>
                        {p.activo ? "Activo" : "Inactivo"}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1.5">
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-7 text-[11.5px] px-2"
                          onClick={(e) => {
                            e.stopPropagation();
                            abrir(p);
                          }}
                          data-testid={`btn-editar-prof-${p.id}`}
                        >
                          <Pencil className="size-3 mr-1" /> Editar
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-7 text-[11.5px] px-2"
                          disabled={actualizar.isPending}
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleActivo(p);
                          }}
                          data-testid={`btn-toggle-prof-${p.id}`}
                        >
                          {p.activo ? (
                            <>
                              <UserX className="size-3 mr-1" /> Desactivar
                            </>
                          ) : (
                            <>
                              <UserCheck className="size-3 mr-1" /> Activar
                            </>
                          )}
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <DetalleProfesionalDialog profesional={detalle} onClose={() => setDetalle(null)} />
      <ProfesionalDialog open={dialogOpen} onOpenChange={setDialogOpen} profesional={editando} />
    </div>
  );
}
