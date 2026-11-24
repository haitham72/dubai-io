import { beforeEach, describe, expect, it, vi } from "vitest";

const store = new Map<string, string>();

vi.mock("@react-native-async-storage/async-storage", () => ({
  default: {
    getItem: vi.fn(async (key: string) => store.get(key) ?? null),
    setItem: vi.fn(async (key: string, val: string) => {
      store.set(key, val);
    }),
    removeItem: vi.fn(async (key: string) => {
      store.delete(key);
    }),
  },
}));

import {
  clearUrlOverride,
  loadUrlOverride,
  saveUrlOverride,
} from "../src/storage/urlOverride";

describe("urlOverride storage", () => {
  beforeEach(() => {
    store.clear();
  });

  it("saves, normalizes, loads, and clears LAN URL overrides", async () => {
    expect(await loadUrlOverride()).toBeNull();

    await saveUrlOverride("192.168.1.55:3060/");
    expect(await loadUrlOverride()).toBe("http://192.168.1.55:3060");

    await clearUrlOverride();
    expect(await loadUrlOverride()).toBeNull();
  });

  it("rejects invalid override URLs before persisting", async () => {
    await expect(saveUrlOverride("javascript:alert(1)")).rejects.toThrow();
    expect(await loadUrlOverride()).toBeNull();
  });
});
