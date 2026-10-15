import { FileText } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { PestanaBloqueadaError, abrirArchivoDeControl } from "./api";
import { useArchivosDeControl } from "./hooks";

function fmtFechaHora(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [fecha, hora = ""] = iso.split("T");
  const [a, m, d] = fecha.split("-");
  return `${d}-${m}-${a} ${hora.slice(0, 5)}`.trim();
}

interface Props {
  controlId: number;
}

/** Documentos que el médico subió a la biblioteca de SALUTEM para este control. */
export function DocumentosSalutem({ controlId }: Props) {
  const { data: archivos = [], isLoading, isError } = useArchivosDeControl(controlId);

  const ver = async (archivoId: number, nombre: string) => {
    try {
      await abrirArchivoDeControl(controlId, archivoId, nombre);
    } catch (e) {
      if (e instanceof PestanaBloqueadaError) {
        toast.error("El navegador bloqueó la pestaña nueva. Permite ventanas emergentes para este sitio.");
        return;
      }
      toast.error("No se pudo abrir el documento. SALUTEM no lo entregó; ábrelo directamente en SALUTEM.");
    }
  };

  return (
    <div data-testid={`documentos-salutem-${controlId}`}>
      <p className="mb-1.5 text-[11.5px] font-medium uppercase tracking-wide text-muted-foreground">
        Documentos en SALUTEM
      </p>
      {isLoading ? (
        <p className="text-[13px] text-muted-foreground">Cargando documentos…</p>
      ) : isError ? (
        <p className="text-[13px] text-destructive">No se pudieron cargar los documentos de SALUTEM.</p>
      ) : archivos.length === 0 ? (
        <p className="text-[13px] text-muted-foreground">
          Sin documentos en la biblioteca de SALUTEM para este control.
        </p>
      ) : (
        <ul className="space-y-1">
          {archivos.map((a) => (
            <li key={a.archivo_id} className="flex items-center gap-2 text-[13px]">
              <FileText className="size-3.5 text-muted-foreground" />
              <span className="truncate">{a.nombre}</span>
              <span className="font-mono text-[11.5px] text-muted-foreground">
                {fmtFechaHora(a.fecha_creacion)}
              </span>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="ml-auto h-7"
                aria-label={`Ver ${a.nombre}`}
                onClick={() => ver(a.archivo_id, a.nombre)}
              >
                Ver
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
