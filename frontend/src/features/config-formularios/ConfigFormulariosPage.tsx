/**
 * ConfigFormulariosPage — editor de formularios dinámicos (EPIC-11, CEPA-110/111).
 *
 * Flujo: cargar un formulario por su clave → ver la versión publicada → editar
 * un borrador (agregar/editar/quitar campos) → guardar → publicar. La publicación
 * pasa por el validador del backend: si falla, se muestran los errores de
 * parametrización (CEPA-111) y la versión queda en borrador.
 *
 * RBAC: edición solo Coordinación; el resto de roles puede consultar la versión
 * publicada (lectura).
 */
import { useState } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import {
  Hash,
  Plus,
  Trash2,
  Settings2,
  AlertCircle,
  CheckCircle2,
  Lock,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth/AuthContext";
import { type Rol } from "@/lib/rbac";
import { usePublicada, useCrearBorrador, usePublicar } from "./hooks";
import {
  editorSchema,
  rowToFieldDefIn,
  missingSystemRows,
  EMPTY_ROW,
  type EditorForm,
  type FieldRow,
} from "./fieldSchema";
import {
  FIELD_TYPES,
  FIELD_TYPE_LABELS,
  type FieldType,
  type FormVersionRead,
  type PublishResult,
} from "./api";

const inputCls = "h-8 text-[12.5px]";
const selectCls =
  "flex h-8 w-full rounded-md border border-input bg-transparent px-2 text-[12.5px] shadow-sm focus:outline-none focus:ring-1 focus:ring-ring";

function versionToRows(v: FormVersionRead): FieldRow[] {
  return [...v.fields]
    .sort((a, b) => a.display_order - b.display_order)
    .map((f) => ({
      field_key: f.field_key,
      label: f.label,
      field_type: (f.field_type ?? "") as FieldRow["field_type"],
      required: f.required,
      active: f.active,
      system_locked: f.system_locked,
      display_order: f.display_order,
      domain_values_text: (f.domain_values ?? []).join(", "),
    }));
}

// ── Editor de campos ────────────────────────────────────────────────────────

interface EditorProps {
  formKey: string;
  initial: FieldRow[];
  onCancel: () => void;
  onPublished: () => void;
}

function FieldsEditor({ formKey, initial, onCancel, onPublished }: EditorProps) {
  const crear = useCrearBorrador();
  const publicarM = usePublicar();
  const [draftId, setDraftId] = useState<number | null>(null);
  const [publishResult, setPublishResult] = useState<PublishResult | null>(null);

  const {
    register,
    control,
    handleSubmit,
    watch,
    getValues,
    formState: { errors },
  } = useForm<EditorForm>({
    resolver: zodResolver(editorSchema),
    defaultValues: { fields: initial.length ? initial : [EMPTY_ROW] },
  });

  const { fields, append, remove } = useFieldArray({ control, name: "fields" });

  function agregarSistema() {
    const faltantes = missingSystemRows(getValues().fields);
    if (faltantes.length === 0) {
      toast.info("Los campos de sistema ya están presentes");
      return;
    }
    faltantes.forEach((f) => append(f));
  }

  async function guardar(values: EditorForm) {
    try {
      const payload = values.fields.map((f, i) => rowToFieldDefIn(f, i));
      const version = await crear.mutateAsync({ formKey, fields: payload });
      setDraftId(version.id);
      setPublishResult(null);
      toast.success(`Borrador v${version.version_num} guardado`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error al guardar");
    }
  }

  async function onPublicar() {
    if (draftId == null) return;
    try {
      const result = await publicarM.mutateAsync({ formKey, versionId: draftId });
      setPublishResult(result);
      if (result.success) {
        toast.success("Versión publicada");
        onPublished();
      } else {
        toast.error("Publicación bloqueada: revisa los errores");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error al publicar");
    }
  }

  return (
    <Card className="p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-[14px] font-semibold">Editor de borrador</h3>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="h-7 text-[11.5px] px-2"
            onClick={agregarSistema}
            data-testid="btn-agregar-sistema"
            title="Inserta los campos obligatorios del sistema requeridos para publicar"
          >
            <Lock className="size-3 mr-1" /> Campos de sistema
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-7 text-[11.5px] px-2"
            onClick={() => append({ ...EMPTY_ROW })}
            data-testid="btn-agregar-campo"
          >
            <Plus className="size-3 mr-1" /> Agregar campo
          </Button>
        </div>
      </div>

      <form onSubmit={handleSubmit(guardar)} className="space-y-3">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-[11px] uppercase tracking-wider text-muted-foreground">
                <th className="text-left px-2 py-2 font-semibold">Clave</th>
                <th className="text-left px-2 py-2 font-semibold">Etiqueta</th>
                <th className="text-left px-2 py-2 font-semibold">Tipo</th>
                <th className="text-left px-2 py-2 font-semibold">Valores (select)</th>
                <th className="text-center px-2 py-2 font-semibold">Req.</th>
                <th className="text-center px-2 py-2 font-semibold">Activo</th>
                <th className="px-2 py-2"> </th>
              </tr>
            </thead>
            <tbody>
              {fields.map((f, i) => {
                const tipo = watch(`fields.${i}.field_type`);
                const locked = watch(`fields.${i}.system_locked`);
                const rowErr = errors.fields?.[i];
                return (
                  <tr key={f.id} className="border-b align-top" data-testid={`fila-campo-${i}`}>
                    <td className="px-2 py-2">
                      <div className="flex items-center gap-1">
                        {locked && (
                          <Lock
                            className="size-3 text-muted-foreground shrink-0"
                            aria-label="Campo de sistema"
                          />
                        )}
                        <Input
                          className={cn(
                            inputCls,
                            "font-mono w-[120px]",
                            locked && "bg-muted/50 text-muted-foreground",
                          )}
                          placeholder="rut"
                          readOnly={locked}
                          {...register(`fields.${i}.field_key`)}
                        />
                      </div>
                      {rowErr?.field_key && (
                        <p className="text-[10.5px] text-destructive mt-0.5">
                          {rowErr.field_key.message}
                        </p>
                      )}
                    </td>
                    <td className="px-2 py-2">
                      <Input
                        className={cn(inputCls, "w-[150px]")}
                        placeholder="RUT del paciente"
                        {...register(`fields.${i}.label`)}
                      />
                      {rowErr?.label && (
                        <p className="text-[10.5px] text-destructive mt-0.5">
                          {rowErr.label.message}
                        </p>
                      )}
                    </td>
                    <td className="px-2 py-2">
                      <select
                        className={cn(selectCls, "w-[110px]")}
                        {...register(`fields.${i}.field_type`)}
                      >
                        {FIELD_TYPES.map((t) => (
                          <option key={t} value={t}>
                            {FIELD_TYPE_LABELS[t as FieldType]}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-2 py-2">
                      <Input
                        className={cn(inputCls, "w-[160px]")}
                        placeholder="A, B, C"
                        disabled={tipo !== "select"}
                        {...register(`fields.${i}.domain_values_text`)}
                      />
                      {rowErr?.domain_values_text && (
                        <p className="text-[10.5px] text-destructive mt-0.5">
                          {rowErr.domain_values_text.message}
                        </p>
                      )}
                    </td>
                    <td className="px-2 py-2 text-center">
                      <input type="checkbox" {...register(`fields.${i}.required`)} />
                    </td>
                    <td className="px-2 py-2 text-center">
                      <input type="checkbox" {...register(`fields.${i}.active`)} />
                    </td>
                    <td className="px-2 py-2 text-right">
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        className="size-7 p-0"
                        onClick={() => remove(i)}
                        disabled={fields.length === 1}
                        aria-label="Eliminar campo"
                        data-testid={`btn-eliminar-${i}`}
                      >
                        <Trash2 className="size-3.5 text-muted-foreground" />
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {typeof errors.fields?.message === "string" && (
          <p className="text-[11.5px] text-destructive">{errors.fields.message}</p>
        )}

        <div className="flex items-center gap-2">
          <Button type="submit" size="sm" disabled={crear.isPending}>
            {crear.isPending ? "Guardando…" : "Guardar borrador"}
          </Button>
          {draftId != null && (
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={onPublicar}
              disabled={publicarM.isPending}
              data-testid="btn-publicar"
            >
              <CheckCircle2 className="size-3.5 mr-1" />
              {publicarM.isPending ? "Publicando…" : "Publicar borrador"}
            </Button>
          )}
          <Button type="button" size="sm" variant="ghost" onClick={onCancel}>
            Cancelar
          </Button>
        </div>
      </form>

      {/* Errores de parametrización al publicar (CEPA-111) */}
      {publishResult && !publishResult.success && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 space-y-1.5">
          <div className="flex items-center gap-2 text-[12.5px] font-semibold text-destructive">
            <AlertCircle className="size-4" /> Publicación bloqueada — corrige y vuelve a guardar
          </div>
          <ul className="list-disc pl-6 text-[12px] text-destructive space-y-0.5">
            {publishResult.errors.map((e, i) => (
              <li key={i}>
                <span className="font-mono">{e.field_key || "—"}</span>: {e.error}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}

// ── Página ──────────────────────────────────────────────────────────────────

export function ConfigFormulariosPage() {
  const { rol } = useAuth();
  const canWrite = (rol as Rol) === "Coordinacion";

  const [keyInput, setKeyInput] = useState("");
  const [formKey, setFormKey] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);

  const { data: publicada, isLoading, isFetching } = usePublicada(formKey);

  function cargar() {
    const k = keyInput.trim();
    if (!k) return;
    setFormKey(k);
    setEditing(false);
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight">
          Formularios dinámicos
        </h1>
        <p className="text-[13px] text-muted-foreground mt-1">
          Parametrización de campos configurables · {canWrite ? "edición Coordinación" : "solo lectura"}
        </p>
      </div>

      {/* Cargar por clave */}
      <div className="flex items-center gap-2">
        <Hash className="size-3.5 text-muted-foreground shrink-0" />
        <Input
          value={keyInput}
          onChange={(e) => setKeyInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") cargar();
          }}
          placeholder="Clave del formulario (ej. ficha_clinica)"
          className="h-9 w-[280px] text-[13px]"
          aria-label="Clave del formulario"
          data-testid="input-form-key"
        />
        <Button
          size="sm"
          variant="outline"
          onClick={cargar}
          disabled={!keyInput.trim()}
          data-testid="btn-cargar"
        >
          Cargar
        </Button>
      </div>

      {formKey === null ? (
        <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-12 text-center">
          <Settings2 className="mx-auto mb-3 size-8 text-muted-foreground/50" />
          <p className="text-[13.5px] text-muted-foreground">
            Carga un formulario por su clave para ver o editar su definición.
          </p>
        </div>
      ) : isLoading || isFetching ? (
        <p className="text-[13px] text-muted-foreground px-1">Cargando…</p>
      ) : (
        <div className="space-y-4">
          {/* Versión publicada (lectura) */}
          <Card className="p-5 space-y-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="text-[14px] font-semibold">
                  Formulario «{formKey}»
                </h3>
                {publicada ? (
                  <p className="text-[12px] text-muted-foreground">
                    Versión publicada v{publicada.version_num} ·{" "}
                    {publicada.fields.length} campo(s)
                  </p>
                ) : (
                  <p className="text-[12px] text-muted-foreground">
                    Sin versión publicada todavía.
                  </p>
                )}
              </div>
              {canWrite && !editing && (
                <Button
                  size="sm"
                  onClick={() => setEditing(true)}
                  data-testid="btn-editar-borrador"
                >
                  {publicada ? "Editar como nuevo borrador" : "Crear primer borrador"}
                </Button>
              )}
            </div>

            {publicada && publicada.fields.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-muted/30 border-b text-[11px] uppercase tracking-wider text-muted-foreground">
                      <th className="text-left px-3 py-2 font-semibold">Clave</th>
                      <th className="text-left px-3 py-2 font-semibold">Etiqueta</th>
                      <th className="text-left px-3 py-2 font-semibold">Tipo</th>
                      <th className="text-left px-3 py-2 font-semibold">Atributos</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...publicada.fields]
                      .sort((a, b) => a.display_order - b.display_order)
                      .map((f) => (
                        <tr key={f.id} className="border-b">
                          <td className="px-3 py-2 font-mono text-[12px]">
                            {f.field_key}
                          </td>
                          <td className="px-3 py-2 text-[12.5px]">{f.label}</td>
                          <td className="px-3 py-2">
                            <Badge variant="neutral">
                              {FIELD_TYPE_LABELS[f.field_type as FieldType] ??
                                f.field_type ??
                                "—"}
                            </Badge>
                          </td>
                          <td className="px-3 py-2 text-[12px] text-muted-foreground">
                            <span className="inline-flex items-center gap-2">
                              {f.required && <span>Requerido</span>}
                              {!f.active && <span>Inactivo</span>}
                              {f.system_locked && (
                                <span className="inline-flex items-center gap-1">
                                  <Lock className="size-3" /> Sistema
                                </span>
                              )}
                            </span>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          {/* Editor */}
          {canWrite && editing && (
            <FieldsEditor
              formKey={formKey}
              initial={publicada ? versionToRows(publicada) : []}
              onCancel={() => setEditing(false)}
              onPublished={() => setEditing(false)}
            />
          )}
        </div>
      )}
    </div>
  );
}
