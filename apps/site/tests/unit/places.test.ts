import { expect, test } from "vitest";
import { mapsHref, placesQueryFromTurn, wantsNearbyPlaces } from "../../unified/data/places";

test("wantsNearbyPlaces trusts places_near and nearby+venue wording", () => {
  expect(wantsNearbyPlaces("anything", "places_near")).toBe(true);
  expect(wantsNearbyPlaces("Gyms near Dubai Marina open now")).toBe(true);
  expect(wantsNearbyPlaces("good coffee nearby")).toBe(true);
  expect(wantsNearbyPlaces("I left my bag in a taxi")).toBe(false);
  expect(wantsNearbyPlaces("Year 5 British curriculum")).toBe(false);
});

test("placesQueryFromTurn prefers Luna query slot", () => {
  expect(placesQueryFromTurn({ intent: "places_near", query: "lasagna" }, "I want lasagna")).toBe(
    "lasagna near Dubai Marina",
  );
});

test("placesQueryFromTurn uses category label when no query", () => {
  expect(placesQueryFromTurn({ intent: "places_near", category: "coffee" }, "coffee nearby")).toBe(
    "coffee shops near Dubai Marina",
  );
  expect(placesQueryFromTurn({ intent: "places_near", category: "pets", subcategory: "Vet" }, "vet")).toBe(
    "Vet pet services near Dubai Marina",
  );
});

test("placesQueryFromTurn falls back to clipped user text", () => {
  expect(placesQueryFromTurn({ intent: "places_near" }, "  Gyms near Dubai Marina open now  ")).toBe(
    "Gyms near Dubai Marina open now",
  );
  expect(placesQueryFromTurn({ intent: "places_near" }, "coffee nearby")).toBe(
    "coffee nearby near Dubai Marina",
  );
});

test("mapsHref only allows Google Maps https links", () => {
  expect(mapsHref("https://maps.google.com/?q=x")).toMatch(/^https:/);
  expect(mapsHref("https://www.google.com/maps/place/x")).toMatch(/^https:/);
  expect(mapsHref("https://evil.example/maps")).toBeNull();
  expect(mapsHref("javascript:alert(1)")).toBeNull();
  expect(mapsHref(undefined)).toBeNull();
});
