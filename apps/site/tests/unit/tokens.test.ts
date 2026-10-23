import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, test } from "vitest";

const css = readFileSync(join(__dirname, "../../unified/tokens.css"), "utf8");
const dark = css.slice(css.indexOf(':root[data-theme="dark"]'));
const light = css.slice(0, css.indexOf(':root[data-theme="dark"]'));

describe("tokens.css", () => {
  test("light palette is white + steel-teal", () => {
    expect(light).toMatch(/--accent:\s*#357F92/i);
    expect(light).toMatch(/--bg:\s*#FFFFFF/i);
    expect(light).toMatch(/--surface-2:\s*#F6F7F8/i);
    expect(light).toMatch(/--home-haze:/);
  });

  test("dark palette is Graphite", () => {
    expect(dark).toMatch(/--bg:\s*#141618/i);
    expect(dark).toMatch(/--accent:\s*#6FA9B8/i);
    expect(dark).toMatch(/--home-haze:\s*none/);
  });

  test("no shadows", () => {
    for (const m of css.matchAll(/box-shadow\s*:\s*([^;]+);/g)) expect(m[1].trim()).toBe("none");
    for (const m of css.matchAll(/--shadow[\w-]*\s*:\s*([^;]+);/g)) expect(m[1].trim()).toBe("none");
  });
});
