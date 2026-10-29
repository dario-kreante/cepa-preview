import type { ReactNode } from "react";
import { FileText } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  PestanaBloqueadaError,
  abrirArchivoDeAtencion,
  abrirArchivoDeControl,
  abrirDocumentoDePaciente,
  type DocumentoSalutemRead,
  type RelacionDocumento,
} from "./api";
import { useArchivosDeAtencion, useArchivosDeControl, useDocumentosDePaciente } from "./hooks";

function fmtFechaHora(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [fecha, hora = ""] = iso.split("T");
  const [a, m, d] = fecha.split("-");
  return `${d}-${m}-${a} ${hora.slice(0, 5)}`.trim();
}

/** Abre un documento de SALUTEM y avisa con un toast si no se pudo. */
async function verDocumento(abrir: () => Promise<void>) {
  try {
    await abrir();
  } catch (e) {
    if (e instanceof PestanaBloqueadaError) {
      toast.error("El navegador bloqueó la pestaña nueva. Permite ventanas emergentes para este sitio.");
      return;
    }
    toast.error("No se pudo abrir el documento. SALUTEM no lo entregó; ábrelo directamente en SALUTEM.");
  }
}

interface DocumentoListable {
  archivo_id: number;
  nombre: string;
  fecha_creacion?: string | null;
}

interface ListaProps<T extends DocumentoListable> {
  documentos: T[];
  isLoading: boolean;
  isError: boolean;
  vacio: string;
  onVer: (doc: T) => void;
  /** Marcas extra junto al nombre (p. ej. la relación deducida con licencia o receta). */
  extra?: (doc: T) => ReactNode;
}

/** Lista de documentos de SALUTEM con su botón «Ver»; la comparten controles y módulos. */
export function ListaDocumentosSalutem<T extends DocumentoListable>({
  documentos,
  isLoading,
  isError,
  vacio,
  onVer,
  extra,
}: ListaProps<T>) {
  if (isLoading) return <p className="text-[13px] text-muted-foreground">Cargando documentos…</p>;
  if (isError)
    return <p className="text-[13px] text-destructive">No se pudieron cargar los documentos de SALUTEM.</p>;
  if (documentos.length === 0) return <p className="text-[13px] text-muted-foreground">{vacio}</p>;
  return (
    <ul className="space-y-1">
      {documentos.map((a) => (
        <li key={a.archivo_id} className="flex items-center gap-2 text-[13px]">
          <FileText className="size-3.5 shrink-0 text-muted-foreground" />
          <span className="truncate">{a.nombre}</span>
          {extra?.(a)}
          <span className="font-mono text-[11.5px] text-muted-foreground">{fmtFechaHora(a.fecha_creacion)}</span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="ml-auto h-7"
            aria-label={`Ver ${a.nombre}`}
            onClick={() => onVer(a)}
          >
            Ver
          </Button>
        </li>
      ))}
    </ul>
  );
}

type Props =
  | { controlId: number; citaId?: undefined }
  /** Atención médica que no es control (p. ej. una Evaluación médica). */
  | { citaId: number; controlId?: undefined };

/** Documentos que el médico subió a la biblioteca de SALUTEM para este control o atención. */
export function DocumentosSalutem({ controlId, citaId }: Props) {
  const deControl = useArchivosDeControl(controlId ?? 0, controlId !== undefined);
  const deAtencion = useArchivosDeAtencion(citaId ?? 0, citaId !== undefined);
  const { data: archivos = [], isLoading, isError } = controlId !== undefined ? deControl : deAtencion;

  return (
    <div data-testid={controlId !== undefined ? `documentos-salutem-${controlId}` : `documentos-atencion-${citaId}`}>
      <p className="mb-1.5 text-[11.5px] font-medium uppercase tracking-wide text-muted-foreground">
        Documentos en SALUTEM
      </p>
      <ListaDocumentosSalutem
        documentos={archivos}
        isLoading={isLoading}
        isError={isError}
        vacio={`Sin documentos en la biblioteca de SALUTEM para ${controlId !== undefined ? "este control" : "esta atención"}.`}
        onVer={(a) =>
          verDocumento(() =>
            controlId !== undefined
              ? abrirArchivoDeControl(controlId, a.archivo_id, a.nombre)
              : abrirArchivoDeAtencion(citaId!, a.archivo_id, a.nombre),
          )
        }
      />
    </div>
  );
}

function fmtFecha(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [a, m, d] = iso.split("-");
  return `${d}-${m}-${a}`;
}

const NOTA_RELACION: Record<RelacionDocumento, string> = {
  licencia:
    "SALUTEM no informa en qué carpeta está cada documento. Se muestran los subidos el día de una atención que indicó licencia o reposo, o hasta 7 días después.",
  receta:
    "SALUTEM no informa en qué carpeta está cada documento. Se muestran los subidos el día de una atención que indicó una receta, o hasta 7 días después.",
};

interface PacienteProps {
  pacienteId: number;
  titulo: string;
  /** Sin relación se lista toda la biblioteca, marcando la relación deducida de cada documento. */
  relacion?: RelacionDocumento;
}

/** Biblioteca de SALUTEM del paciente (no de un control), para Licencias, Fármacos y Controles. */
export function DocumentosSalutemPaciente({ pacienteId, titulo, relacion }: PacienteProps) {
  const { data: documentos = [], isLoading, isError } = useDocumentosDePaciente(pacienteId, relacion);

  const marcas = (d: DocumentoSalutemRead) =>
    relacion ? null : (
      <span className="flex shrink-0 items-center gap-1">
        {d.licencia && <Badge variant="warning">Licencia</Badge>}
        {d.receta && <Badge variant="info">Receta</Badge>}
        {d.fecha_atencion && (
          <span className="text-[11.5px] text-muted-foreground">atención {fmtFecha(d.fecha_atencion)}</span>
        )}
      </span>
    );

  return (
    <section
      className="space-y-2 rounded-lg border bg-card px-4 py-3"
      data-testid={`documentos-paciente-${relacion ?? "todos"}`}
      aria-label={titulo}
    >
      <div>
        <h2 className="text-[14px] font-semibold">{titulo}</h2>
        <p className="mt-0.5 text-[12px] text-muted-foreground">
          {relacion
            ? NOTA_RELACION[relacion]
            : "Biblioteca del paciente en SALUTEM: no son documentos de un control en particular. SALUTEM no informa la carpeta; «Licencia» y «Receta» indican que el documento se subió el día de una atención que las indicó, o hasta 7 días después."}
        </p>
      </div>
      <ListaDocumentosSalutem
        documentos={documentos}
        isLoading={isLoading}
        isError={isError}
        vacio={
          relacion === "licencia"
            ? "Sin documentos de licencias en SALUTEM para este paciente."
            : relacion === "receta"
              ? "Sin recetas en SALUTEM para este paciente."
              : "Sin documentos en la biblioteca de SALUTEM para este paciente."
        }
        onVer={(d) => verDocumento(() => abrirDocumentoDePaciente(pacienteId, d.archivo_id, d.nombre))}
        extra={marcas}
      />
    </section>
  );
}
