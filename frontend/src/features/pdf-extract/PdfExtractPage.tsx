/**
 * PdfExtractPage — lectura de documentos PDF (CEPA-112, P1).
 *
 * Flujo: subir un PDF → el backend extrae texto y sugiere campos (mapeo
 * heurístico) → el administrativo revisa/edita los valores → confirma contra
 * un formulario publicado (valida requeridos y dominios). La extracción degrada
 * con gracia: si falla, se muestra el motivo sin bloquear la captura manual.
 *
 * RBAC: carga y confirmación para Coordinación y Administrativo (Auditor no).
 */
import { useRef, useState } from "react";
import { toast } from "sonner";
import {
  Upload,
  FileText,
  Plus,
  Trash2,
  CheckCircle2,
  AlertCircle,
  ShieldCheck,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth/AuthContext";
import { puedeEscribir, type Rol } from "@/lib/rbac";
import { useConfirmExtraction, useUploadPdf } from "./hooks";
import type { ExtractedFieldOut } from "./api";

export function PdfExtractPage() {
  const { rol } = useAuth();
  const canWrite = puedeEscribir(rol as Rol);

  const fileRef = useRef<HTMLInputElement>(null);
  const upload = useUploadPdf();
  const confirm = useConfirmExtraction();

  const [fileName, setFileName] = useState<string | null>(null);
  const [fields, setFields] = useState<ExtractedFieldOut[]>([]);
  const [rawText, setRawText] = useState<string>("");
  const [extractError, setExtractError] = useState<string | null>(null);
  const [extracted, setExtracted] = useState(false);
  const [formKey, setFormKey] = useState("");
  const [showRaw, setShowRaw] = useState(false);

  if (!canWrite) {
    return (
      <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-16 text-center">
        <ShieldCheck className="mx-auto mb-3 size-8 text-muted-foreground/50" />
        <p className="text-[13.5px] text-muted-foreground">
          La lectura de PDF está disponible para Coordinación y Administrativo.
        </p>
      </div>
    );
  }

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    setExtracted(false);
    setExtractError(null);
    try {
      const result = await upload.mutateAsync(file);
      setExtracted(true);
      if (result.success) {
        setFields(result.fields);
        setRawText(result.raw_text);
        setExtractError(null);
        toast.success(`PDF procesado: ${result.fields.length} campo(s) detectado(s)`);
      } else {
        setFields([]);
        setRawText("");
        setExtractError(result.error_message ?? "No se pudo extraer el contenido.");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error al subir el PDF");
    }
  }

  function updateField(i: number, patch: Partial<ExtractedFieldOut>) {
    setFields((prev) => prev.map((f, idx) => (idx === i ? { ...f, ...patch } : f)));
  }
  function removeField(i: number) {
    setFields((prev) => prev.filter((_, idx) => idx !== i));
  }
  function addField() {
    setFields((prev) => [...prev, { field_key: "", value: "" }]);
  }

  async function onConfirm() {
    if (!formKey.trim()) {
      toast.error("Indica la clave del formulario destino.");
      return;
    }
    const limpios = fields.filter((f) => f.field_key.trim());
    try {
      const res = await confirm.mutateAsync({
        formKey: formKey.trim(),
        fields: limpios,
      });
      toast.success(`Confirmado: ${res.received_fields} campo(s) recibidos`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error al confirmar");
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight">
          Lectura de documentos PDF
        </h1>
        <p className="text-[13px] text-muted-foreground mt-1">
          Sube un PDF para pre-llenar campos · revisa y confirma contra un formulario
        </p>
      </div>

      {/* Carga */}
      <Card className="p-5">
        <div className="flex flex-wrap items-center gap-3">
          <input
            ref={fileRef}
            type="file"
            accept="application/pdf,.pdf"
            className="hidden"
            onChange={onFile}
            data-testid="input-pdf"
          />
          <Button
            size="sm"
            onClick={() => fileRef.current?.click()}
            disabled={upload.isPending}
            data-testid="btn-subir-pdf"
          >
            <Upload className="size-3.5" />
            {upload.isPending ? "Procesando…" : "Subir PDF"}
          </Button>
          {fileName && (
            <span className="text-[12.5px] text-muted-foreground inline-flex items-center gap-1.5">
              <FileText className="size-3.5" /> {fileName}
            </span>
          )}
        </div>
      </Card>

      {/* Error de extracción (degradación gracia) */}
      {extractError && (
        <div className="rounded-lg border border-[oklch(0.85_0.08_85)] bg-[oklch(0.97_0.04_85)] px-4 py-3 flex items-start gap-2">
          <AlertCircle className="size-4 text-[oklch(0.52_0.16_75)] mt-0.5 shrink-0" />
          <div className="text-[12.5px]">
            <p className="font-semibold text-[oklch(0.45_0.16_75)]">
              No se pudo extraer el contenido
            </p>
            <p className="text-muted-foreground">
              {extractError} Puedes capturar los datos manualmente más abajo.
            </p>
          </div>
        </div>
      )}

      {/* Campos extraídos / editables */}
      {extracted && (
        <Card className="p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-[14px] font-semibold">
              Campos detectados ({fields.length})
            </h3>
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-[11.5px] px-2"
              onClick={addField}
              data-testid="btn-agregar-campo"
            >
              <Plus className="size-3 mr-1" /> Agregar campo
            </Button>
          </div>

          {fields.length === 0 ? (
            <p className="text-[13px] text-muted-foreground">
              No se detectaron campos. Agrega los que necesites manualmente.
            </p>
          ) : (
            <div className="space-y-2">
              {fields.map((f, i) => (
                <div key={i} className="flex items-center gap-2" data-testid={`campo-${i}`}>
                  <Input
                    className="h-8 text-[12.5px] font-mono w-[200px]"
                    placeholder="field_key"
                    value={f.field_key}
                    onChange={(e) => updateField(i, { field_key: e.target.value })}
                  />
                  <Input
                    className="h-8 text-[12.5px] flex-1"
                    placeholder="valor"
                    value={f.value}
                    onChange={(e) => updateField(i, { value: e.target.value })}
                  />
                  <Button
                    size="sm"
                    variant="ghost"
                    className="size-7 p-0 shrink-0"
                    onClick={() => removeField(i)}
                    aria-label="Eliminar campo"
                    data-testid={`btn-eliminar-${i}`}
                  >
                    <Trash2 className="size-3.5 text-muted-foreground" />
                  </Button>
                </div>
              ))}
            </div>
          )}

          {/* Confirmación contra formulario */}
          <div className="border-t border-border pt-4 flex flex-wrap items-end gap-3">
            <div>
              <Label htmlFor="form-key-pdf">Formulario destino (clave)</Label>
              <Input
                id="form-key-pdf"
                value={formKey}
                onChange={(e) => setFormKey(e.target.value)}
                placeholder="ej. ficha_clinica"
                className="h-9 w-[220px]"
                data-testid="input-form-key"
              />
            </div>
            <Button
              size="sm"
              onClick={onConfirm}
              disabled={confirm.isPending || fields.length === 0}
              data-testid="btn-confirmar"
            >
              <CheckCircle2 className="size-3.5" />
              {confirm.isPending ? "Confirmando…" : "Confirmar"}
            </Button>
          </div>

          {/* Texto crudo (auditoría / debug) */}
          {rawText && (
            <div>
              <button
                type="button"
                onClick={() => setShowRaw((v) => !v)}
                className="text-[12px] text-muted-foreground hover:text-foreground underline"
              >
                {showRaw ? "Ocultar" : "Ver"} texto extraído
              </button>
              {showRaw && (
                <pre
                  className={cn(
                    "mt-2 max-h-48 overflow-auto rounded-md border border-border bg-muted/30 p-3",
                    "text-[11.5px] whitespace-pre-wrap font-mono text-muted-foreground",
                  )}
                >
                  {rawText}
                </pre>
              )}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
