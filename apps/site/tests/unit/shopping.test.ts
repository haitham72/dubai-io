import { expect, test } from "vitest";
import { wantsProductSearch } from "../../unified/data/shopping";

test("wantsProductSearch trusts product_search and need+item wording", () => {
  expect(wantsProductSearch("x", "product_search")).toBe(true);
  expect(wantsProductSearch("I need a green shirt")).toBe(true);
  expect(wantsProductSearch("find me shampoo")).toBe(true);
  expect(wantsProductSearch("Gyms near Dubai Marina open now")).toBe(false);
  expect(wantsProductSearch("I left my bag in a taxi")).toBe(false);
});
