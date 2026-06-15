import { useParams } from "react-router-dom";
import { useVista360 } from "./hooks";
import { Card } from "@/components/ui/card";

export function Vista360Page() {
  const { id } = useParams();
  const { data, isLoading, isError } = useVista360(Number(id));
  if (isLoading) return <p className="text-ink-400">Cargando…</p>;
  if (isError || !data) return <p className="text-danger-600">No se pudo cargar el paciente.</p>;
  const ranuras: [string, unknown[]][] = [
    ["Fármacos", data.farmacos], ["Licencias", data.licencias],
    ["Controles", data.controles], ["Reintegro", data.reintegro],
  ];
  return (
    <div className="space-y-4 max-w-3xl">
      <h1 className="text-lg font-semibold">{data.paciente.nombre} <span className="text-ink-500 font-normal">· {data.paciente.rut}</span></h1>
      <Card className="p-4">
        <h2 className="font-medium mb-2">Ingresos</h2>
        <ul className="space-y-1 text-sm">
          {data.ingresos.map((i) => (
            <li key={i.id} className="flex justify-between">
              <span>Folio {i.folio}</span><span className="text-ink-500">{i.estado} · {i.fecha_ingreso}</span>
            </li>
          ))}
          {data.ingresos.length === 0 && <li className="text-ink-400">Sin ingresos</li>}
        </ul>
      </Card>
      <div className="grid grid-cols-2 gap-3">
        {ranuras.map(([nombre, items]) => (
          <Card key={nombre} className="p-4">
            <h2 className="font-medium">{nombre}</h2>
            <p className="text-sm text-ink-400">{items.length ? `${items.length} registros` : "Pendiente (módulo futuro)"}</p>
          </Card>
        ))}
      </div>
    </div>
  );
}
