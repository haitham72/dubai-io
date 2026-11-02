import { expect, test } from "vitest";
import { DEMO_SERVICES, filterServices } from "../../unified/services/services-data";

test("filterServices matches category", () => {
  const laundry = filterServices(DEMO_SERVICES, "", "laundry");
  expect(laundry.map((x) => x.id)).toEqual(["marinaexpress"]);
});

test("filterServices matches search text", () => {
  const dewa = filterServices(DEMO_SERVICES, "dewa", "all");
  expect(dewa).toHaveLength(1);
  expect(dewa[0].kind).toBe("portal");
});

test("demo services carry demo_fixture provenance", () => {
  expect(DEMO_SERVICES.every((s) => s.provenance === "demo_fixture")).toBe(true);
});
