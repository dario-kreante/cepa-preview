import { useState } from "react";
import { Link } from "react-router-dom";
import { useBuscarPacientes } from "./hooks";
import { Input } from "@/components/ui/input";

export function BuscarPage() {
  const [q, setQ] = useState("");
  const { data, isFetching } = useBuscarPacientes(q);
  return (
    <div className="space-y-4 max-w-2xl">
      <h1 className="text-lg font-semibold text-ink-900">Búsqueda 360°</h1>
      <Input placeholder="RUT, nombre o folio…" value={q} onChange={(e) => setQ(e.target.value)} />
      {isFetching && <p className="text-sm text-ink-400">Buscando…</p>}
      <ul className="divide-y divide-ink-200 rounded-md border border-ink-200 bg-white">
        {(data ?? []).map((p) => (
          <li key={p.id}>
            <Link to={`/pacientes/${p.id}`} className="flex justify-between px-4 py-3 hover:bg-ink-50">
              <span className="font-medium">{p.nombre}</span>
              <span className="text-ink-500">{p.rut}</span>
            </Link>
          </li>
        ))}
        {q && !isFetching && (data?.length ?? 0) === 0 && (
          <li className="px-4 py-3 text-ink-400 text-sm">Sin resultados</li>
        )}
      </ul>
    </div>
  );
}
