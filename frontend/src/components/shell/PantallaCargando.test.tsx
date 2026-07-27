import { afterEach, describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
import { PantallaCargando } from "./PantallaCargando";

afterEach(() => vi.useRealTimers());

describe("PantallaCargando", () => {
  it("muestra el aviso de arranque en frío cuando la espera se alarga", () => {
    vi.useFakeTimers();
    render(<PantallaCargando />);

    expect(screen.getByText("Cargando…")).toBeInTheDocument();
    expect(screen.queryByText(/despertar/i)).not.toBeInTheDocument();

    act(() => void vi.advanceTimersByTime(6000));

    expect(screen.getByText(/despertar/i)).toBeInTheDocument();
  });
});
