import { beforeEach, describe, expect, it } from "vitest";
import { tokenStore } from "./tokenStore";

describe("tokenStore", () => {
  beforeEach(() => { localStorage.clear(); tokenStore.clear(); });

  it("guarda y lee el access token en memoria (no en localStorage)", () => {
    tokenStore.setAccess("abc");
    expect(tokenStore.getAccess()).toBe("abc");
    expect(localStorage.getItem("cepa_access")).toBeNull();
  });

  it("persiste el refresh token en localStorage", () => {
    tokenStore.setRefresh("ref");
    expect(tokenStore.getRefresh()).toBe("ref");
    expect(localStorage.getItem("cepa_refresh")).toBe("ref");
  });

  it("clear borra ambos", () => {
    tokenStore.setAccess("a"); tokenStore.setRefresh("r");
    tokenStore.clear();
    expect(tokenStore.getAccess()).toBeNull();
    expect(tokenStore.getRefresh()).toBeNull();
  });
});
