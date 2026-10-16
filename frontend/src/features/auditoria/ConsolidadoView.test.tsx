import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ConsolidadoView } from "./ConsolidadoView";
import type { CasoConsolidadoRead } from "./api";

const CASO = {
  ingreso_id: 9,
  datos_caso: {
    folio: "F-2026-0009",
    numero_siniestro: null,
    fecha_denuncia: null,
    tipo_denuncia: null,
    fecha_derivacion: null,
    nombre_completo: "Paciente Sin Rut",
    rut: null,
    region: null,
  },
  evaluaciones: {
    fecha_eval_medica: null,
    fecha_eval_psicologica: null,
    fecha_calificacion_reca: null,
    diagnostico_inicial: null,
    diagnostico_post_reca: null,
  },
  controles: {
    fecha_primera_consulta_medica: null,
    fecha_primera_consulta_psicologica: null,
    reintegro_parcial: false,
    fecha_reintegro_parcial: null,
    reintegro_total: false,
    fecha_reintegro_total: null,
  },
  cierre: {
    alta_medica: false,
    fecha_alta_medica: null,
    alta_psicologica: false,
    fecha_alta_psicologica: null,
    alta_terapeutica: false,
    fecha_alta_terapeutica: null,
    estado_general: null,
    observaciones: null,
  },
} as unknown as CasoConsolidadoRead;

describe("ConsolidadoView", () => {
  it("muestra un guion cuando el paciente no tiene RUT", () => {
    render(<ConsolidadoView caso={CASO} />);
    expect(screen.getByText("Paciente Sin Rut")).toBeInTheDocument();
    expect(screen.getByText("—", { selector: "p.font-mono" })).toBeInTheDocument();
  });
});
