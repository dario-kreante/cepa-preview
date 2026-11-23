import { useState } from "react";
import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { server } from "@/test/msw/server";
import { ConvenioSelect } from "./ConvenioSelect";

const BASE = import.meta.env.VITE_API_BASE_URL;

const ISL = {
  id: 1,
  nombre: "Convenio ISL MAULE",
  salutem_id: 10,
  activo_salutem: true,
  visible: true,
  seleccionable: true,
  sincronizado_en: "2026-11-23T07:10:00Z",
};
const RANGERS = { ...ISL, id: 3, nombre: "Convenio Rangers", salutem_id: null };

function mockCatalogo(sugerido: unknown = null) {
  const consultas: URL[] = [];
  server.use(
    http.get(`${BASE}/api/v1/convenios`, () => HttpResponse.json([ISL, RANGERS])),
    http.get(`${BASE}/api/v1/convenios/sugerido`, ({ request }) => {
      consultas.push(new URL(request.url));
      return HttpResponse.json({ convenio: sugerido });
    }),
  );
  return consultas;
}

function Wrapper({
  inicial = "",
  valorGuardado,
  sugerencia,
}: {
  inicial?: string;
  valorGuardado?: string | null;
  sugerencia?: { paciente_id?: number; rut?: string } | null;
}) {
  const [valor, setValor] = useState(inicial);
  return (
    <>
      <label htmlFor="conv">Convenio</label>
      <ConvenioSelect
        id="conv"
        value={valor}
        onChange={setValor}
        valorGuardado={valorGuardado}
        sugerencia={sugerencia}
      />
    </>
  );
}

function renderSelect(props: Parameters<typeof Wrapper>[0] = {}) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <Wrapper {...props} />
    </QueryClientProvider>,
  );
}

describe("ConvenioSelect", () => {
  it("muestra Sin convenio y los convenios seleccionables", async () => {
    mockCatalogo();
    renderSelect();
    expect(await screen.findByRole("option", { name: "Convenio ISL MAULE" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Convenio Rangers" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Sin convenio" })).toHaveValue("");
    expect(screen.getByLabelText("Convenio")).toHaveValue("");
  });

  it("con valor guardado fuera del catálogo lo muestra y lo conserva", async () => {
    mockCatalogo();
    renderSelect({ inicial: "Convenio Antiguo", valorGuardado: "Convenio Antiguo" });
    await screen.findByRole("option", { name: "Convenio ISL MAULE" });
    expect(screen.getByRole("option", { name: /Convenio Antiguo/ })).toBeInTheDocument();
    expect(screen.getByLabelText("Convenio")).toHaveValue("Convenio Antiguo");
  });

  it("precarga el sugerido y muestra «Sugerido desde SALUTEM»", async () => {
    const consultas = mockCatalogo(ISL);
    renderSelect({ sugerencia: { paciente_id: 7 } });
    await waitFor(() => expect(screen.getByLabelText("Convenio")).toHaveValue("Convenio ISL MAULE"));
    expect(screen.getByText("Sugerido desde SALUTEM")).toBeInTheDocument();
    expect(consultas[0].searchParams.get("paciente_id")).toBe("7");
  });

  it("no pisa una elección del usuario cuando llega la sugerencia", async () => {
    let liberar!: () => void;
    const puerta = new Promise<void>((r) => (liberar = r));
    server.use(
      http.get(`${BASE}/api/v1/convenios`, () => HttpResponse.json([ISL, RANGERS])),
      http.get(`${BASE}/api/v1/convenios/sugerido`, async () => {
        await puerta;
        return HttpResponse.json({ convenio: ISL });
      }),
    );
    renderSelect({ sugerencia: { paciente_id: 7 } });
    const user = userEvent.setup();
    await screen.findByRole("option", { name: "Convenio Rangers" });
    await user.selectOptions(screen.getByLabelText("Convenio"), "Convenio Rangers");
    liberar();
    await new Promise((r) => setTimeout(r, 100));
    expect(screen.getByLabelText("Convenio")).toHaveValue("Convenio Rangers");
    expect(screen.queryByText("Sugerido desde SALUTEM")).not.toBeInTheDocument();
  });

  it("si el usuario vuelve a Sin convenio, la sugerencia no se reaplica", async () => {
    mockCatalogo(ISL);
    renderSelect({ sugerencia: { paciente_id: 7 } });
    const user = userEvent.setup();
    await waitFor(() => expect(screen.getByLabelText("Convenio")).toHaveValue("Convenio ISL MAULE"));
    await user.selectOptions(screen.getByLabelText("Convenio"), "");
    await new Promise((r) => setTimeout(r, 50));
    expect(screen.getByLabelText("Convenio")).toHaveValue("");
    expect(screen.queryByText("Sugerido desde SALUTEM")).not.toBeInTheDocument();
  });

  it("sin sugerencia (null) queda en Sin convenio y no consulta", async () => {
    const consultas = mockCatalogo(ISL);
    renderSelect({ sugerencia: null });
    await screen.findByRole("option", { name: "Convenio ISL MAULE" });
    await new Promise((r) => setTimeout(r, 50));
    expect(screen.getByLabelText("Convenio")).toHaveValue("");
    expect(consultas).toHaveLength(0);
  });

  it("si el historial no sugiere nada, queda en Sin convenio", async () => {
    mockCatalogo(null);
    renderSelect({ sugerencia: { rut: "11.111.111-1" } });
    await screen.findByRole("option", { name: "Convenio ISL MAULE" });
    await new Promise((r) => setTimeout(r, 50));
    expect(screen.getByLabelText("Convenio")).toHaveValue("");
    expect(screen.queryByText("Sugerido desde SALUTEM")).not.toBeInTheDocument();
  });
});
