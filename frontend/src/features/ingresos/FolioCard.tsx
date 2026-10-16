/**
 * Folio del ingreso en la ficha lateral. Todos lo ven; solo la Administrativa lo
 * corrige ahí mismo. El cambio arrastra reingresos, fichas clínicas e IMED con ese
 * folio (lo resuelve el backend) y queda en la auditoría.
 */
import { useState } from "react";
import { Hash, Pencil } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useCorregirFolio } from "./hooks";

interface FolioCardProps {
  pacienteId: number;
  ingresoId: number;
  folio: string;
  editable: boolean;
}

export function FolioCard({ pacienteId, ingresoId, folio, editable }: FolioCardProps) {
  const [editando, setEditando] = useState(false);
  const [valor, setValor] = useState(folio);
  const corregir = useCorregirFolio(pacienteId);
  const limpio = valor.trim();

  const abrir = () => {
    setValor(folio);
    corregir.reset();
    setEditando(true);
  };

  const guardar = (e: React.FormEvent) => {
    e.preventDefault();
    if (!limpio || limpio === folio) {
      setEditando(false);
      return;
    }
    corregir.mutate({ ingresoId, folio: limpio }, { onSuccess: () => setEditando(false) });
  };

  return (
    <Card>
      <CardContent className="p-3.5 flex items-center gap-3">
        <div className="size-9 rounded-md bg-muted grid place-items-center text-muted-foreground shrink-0">
          <Hash className="size-4" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[10.5px] font-bold uppercase tracking-wider text-muted-foreground">
            Folio
          </div>
          {editando ? (
            <form onSubmit={guardar} className="mt-1 space-y-1.5">
              <div className="flex gap-2">
                <Input
                  autoFocus
                  aria-label="Folio nuevo"
                  value={valor}
                  maxLength={30}
                  onChange={(e) => setValor(e.target.value)}
                  className="h-8 font-mono text-[12.5px]"
                />
                <Button type="submit" size="sm" className="h-8" disabled={!limpio || corregir.isPending}>
                  {corregir.isPending ? "Guardando…" : "Guardar"}
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  className="h-8"
                  onClick={() => setEditando(false)}
                  disabled={corregir.isPending}
                >
                  Cancelar
                </Button>
              </div>
              {corregir.error ? (
                <p role="alert" className="text-[11px] text-destructive">
                  {corregir.error.message}
                </p>
              ) : (
                <p className="text-[11px] text-muted-foreground">
                  El cambio se aplica también a los reingresos y a las fichas con este folio.
                </p>
              )}
            </form>
          ) : (
            <div className="text-[12.5px] font-semibold font-mono truncate">{folio}</div>
          )}
        </div>
        {editable && !editando && (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="h-8 shrink-0"
            onClick={abrir}
            aria-label="Editar folio"
          >
            <Pencil className="size-3.5" /> Editar
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
