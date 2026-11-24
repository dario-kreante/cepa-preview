/** QA-005 (plazos automáticos, fecha de envío) y QA-002 (listas y mes derivado). */
import { describe, it, expect } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { PlazosEptPanel } from "./PlazosEptPanel";
import { ProcesoEptPanel } from "./ProcesoEptPanel";
import { NuevoCasoEptDialog } from "./NuevoCasoEptDialog";
import { mesDesdeFecha } from "./casoEptSchema";
import { opcionesConValorActual } from "./procesoEptSchema";

const BASE = import.meta.env.VITE_API_BASE_URL;
// Payload: {"sub":"1","username":"admin","role":"Administrativo","type":"access","exp":9999999999}
const ADMIN_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJhZG1pbiIsInJvbGUiOiJBZG1pbmlzdHJhdGl2byIsInR5cGUiOiJhY2Nlc3MiLCJleHAiOjk5OTk5OTk5OTl9." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";
const CASO_ID = 31;

const CASO = {
  id: CASO_ID, ingreso_id: 1, mes: "Enero 2026", fecha_ingreso_ept: "2026-01-10",
  nombre_trabajador: "P", rut_trabajador: "1-9", region_trabajador: "Maule", eista: "E",
  factor_riesgo: "sobrecarga", factores_adicionales: [], corresponde_ept: true,
  estado: "abierto", razon_social: null, unidad_cargo_horario: null, contactos: [],
  created_at: "2026-01-10T10:00:00Z", updated_at: "2026-01-10T10:00:00Z",
};

function wrap(ui: React.ReactElement) {
  tokenStore.setAccess(ADMIN_TOKEN);
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <AuthProvider>{ui}</AuthProvider>
    </QueryClientProvider>,
  );
}

describe("helpers", () => {
  it("mes derivado de la fecha de ingreso", () => {
    expect(mesDesdeFecha("2026-01-20")).toBe("Enero 2026");
    expect(mesDesdeFecha("2026-09-01")).toBe("Septiembre 2026");
    expect(mesDesdeFecha("")).toBe("");
  });

  it("un valor antiguo fuera de la lista se conserva como opción", () => {
    expect(opcionesConValorActual(["Sí", "No"], "Parcial")).toEqual(["Parcial", "Sí", "No"]);
    expect(opcionesConValorActual(["Sí", "No"], "Sí")).toEqual(["Sí", "No"]);
    expect(opcionesConValorActual(["Sí", "No"], null)).toEqual(["Sí", "No"]);
  });
});

describe("PlazosEptDialog (QA-005)", () => {
  it("al registrar propone los plazos que calcula el backend, deja ajustarlos y manda la fecha de envío", async () => {
    let post: Record<string, unknown> | undefined;
    let patch: Record<string, unknown> | undefined;
    server.use(
      http.get(`${BASE}/api/v1/casos-ept/:casoId`, () => HttpResponse.json(CASO)),
      // QA-009: ingreso 10-01 + 15 = domingo 25 → viernes 23; + 19 = jueves 29.
      http.get(`${BASE}/api/v1/casos-ept/:casoId/plazos-sugeridos`, () =>
        HttpResponse.json({ plazo_informe_ept: "2026-01-23", plazo_portal_isl: "2026-01-29" }),
      ),
      http.post(`${BASE}/api/v1/casos-ept/:casoId/plazos`, async ({ request }) => {
        post = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ id: 1, caso_ept_id: CASO_ID }, { status: 201 });
      }),
      http.patch(`${BASE}/api/v1/casos-ept/:casoId/plazos`, async ({ request }) => {
        patch = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ id: 1, caso_ept_id: CASO_ID });
      }),
    );
    wrap(<PlazosEptPanel casoId={CASO_ID} canWrite />);

    await userEvent.click(await screen.findByTestId("btn-registrar-plazos"));
    const informe = (await screen.findByLabelText(/Plazo informe EPT/i)) as HTMLInputElement;
    await waitFor(() => expect(informe.value).toBe("2026-01-23"));
    expect((screen.getByLabelText(/Plazo portal ISL/i) as HTMLInputElement).value).toBe("2026-01-29");
    // proyección visible junto al campo de envío, con la regla del día hábil anterior
    const proyeccion = screen.getByTestId("proyeccion-plazos");
    expect(proyeccion).toHaveTextContent("23/01/2026");
    expect(proyeccion).toHaveTextContent("+ 15 y + 19 días corridos");
    expect(proyeccion).toHaveTextContent("día hábil anterior");
    const envio = screen.getByLabelText(/Fecha de envío/i) as HTMLInputElement;
    expect(envio.type).toBe("date");

    await userEvent.clear(informe);
    await userEvent.type(informe, "2026-01-29"); // ajuste manual
    await userEvent.type(envio, "2026-01-25");
    await userEvent.click(screen.getByRole("button", { name: /Guardar/i }));

    await waitFor(() => expect(patch).toBeDefined());
    expect(post?.plazo_informe_ept).toBe("2026-01-29");
    expect(post?.plazo_portal_isl).toBe("2026-01-29");
    expect(patch).toEqual({ fecha_envio: "2026-01-25" });
  });

  it("al editar no recalcula: conserva los plazos guardados y muestra la proyección", async () => {
    server.use(
      http.get(`${BASE}/api/v1/casos-ept/:casoId`, () => HttpResponse.json(CASO)),
      http.get(`${BASE}/api/v1/casos-ept/:casoId/plazos-sugeridos`, () =>
        HttpResponse.json({ plazo_informe_ept: "2026-01-23", plazo_portal_isl: "2026-01-29" }),
      ),
      http.get(`${BASE}/api/v1/casos-ept/:casoId/plazos`, () =>
        HttpResponse.json({
          id: 1, caso_ept_id: CASO_ID, plazo_informe_ept: "2026-03-15", plazo_portal_isl: null,
          fecha_entrega_isl: null, fecha_envio: null, estado_informe: "en_plazo",
          estado_entrega_isl: "en_plazo", created_at: "2026-01-10T10:00:00Z", updated_at: "2026-01-10T10:00:00Z",
        }),
      ),
    );
    wrap(<PlazosEptPanel casoId={CASO_ID} canWrite />);
    await userEvent.click(await screen.findByTestId("btn-editar-plazos"));
    expect(((await screen.findByLabelText(/Plazo informe EPT/i)) as HTMLInputElement).value).toBe("2026-03-15");
    expect((screen.getByLabelText(/Plazo portal ISL/i) as HTMLInputElement).value).toBe("");
    expect(screen.getByLabelText(/Fecha de envío/i)).toBeInTheDocument();
  });
});

describe("ProcesoEptDialog (QA-002)", () => {
  it("insumos y doc. incumplimiento son listas y un valor antiguo no se pierde", async () => {
    let patch: Record<string, unknown> | undefined;
    server.use(
      http.get(`${BASE}/api/v1/casos-ept/:casoId/proceso`, () =>
        HttpResponse.json({
          id: 1, caso_ept_id: CASO_ID, plazo_evid_denunciante: null, plazo_insumos_empresa: null,
          hay_testigos: false, testigos_cantidad: 0, num_entrevistas: 0,
          insumos_eista: "Enviados el lunes", doc_incumplimiento: "No",
          observaciones: null, created_at: "2026-01-10T10:00:00Z", updated_at: "2026-01-10T10:00:00Z",
        }),
      ),
      http.patch(`${BASE}/api/v1/casos-ept/:casoId/proceso`, async ({ request }) => {
        patch = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({});
      }),
    );
    wrap(<ProcesoEptPanel casoId={CASO_ID} canWrite />);
    await userEvent.click(await screen.findByRole("button", { name: /Editar proceso/i }));

    const insumos = (await screen.findByLabelText(/Insumos para el EPTista/i)) as HTMLSelectElement;
    expect(insumos.tagName).toBe("SELECT");
    expect(Array.from(insumos.options).map((o) => o.value)).toEqual(
      expect.arrayContaining(["Sí", "No", "Pendiente", "Enviados el lunes"]),
    );
    expect(insumos.value).toBe("Enviados el lunes");
    const doc = screen.getByLabelText(/Doc\. incumplimiento/i) as HTMLSelectElement;
    expect(Array.from(doc.options).map((o) => o.value).filter(Boolean)).toEqual(["Sí", "No"]);

    await userEvent.click(screen.getByRole("button", { name: /Guardar/i }));
    await waitFor(() => expect(patch).toBeDefined());
    expect(patch?.insumos_eista).toBe("Enviados el lunes");
    expect(patch?.doc_incumplimiento).toBe("No");
  });
});

describe("NuevoCasoEptDialog (QA-002)", () => {
  it("región en lista (con valor antiguo conservado) y mes derivado de la fecha", async () => {
    wrap(
      <NuevoCasoEptDialog
        ingresoId={1}
        open
        onOpenChange={() => {}}
        onCreated={() => {}}
        casoId={CASO_ID}
        initialValues={{
          fecha_ingreso_ept: "2026-01-10", nombre_trabajador: "P", rut_trabajador: "1-9",
          region_trabajador: "VII Región", eista: "E", factor_riesgo: "sobrecarga",
          factor_adicional_1: "", factor_adicional_2: "", corresponde_ept: true,
        }}
      />,
    );
    expect(screen.queryByLabelText(/^Mes$/i)).toBeNull();
    const region = (await screen.findByLabelText(/Región del trabajador/i)) as HTMLSelectElement;
    expect(region.tagName).toBe("SELECT");
    const valores = Array.from(region.options).map((o) => o.value);
    expect(valores).toContain("Maule");
    expect(valores).toContain("VII Región");
    expect(region.value).toBe("VII Región");
    expect(screen.getByTestId("mes-derivado")).toHaveTextContent("Enero 2026");
  });
});
