import { apiPost } from "./api";

export interface ShopProduct {
  title: string;
  price?: string | null;
  rating?: number | null;
  reviews?: number | null;
  thumbnail?: string | null;
  link?: string | null;
  source?: string | null;
  as_of?: string;
  provenance?: string;
}

export interface ShoppingResult {
  products: ShopProduct[];
  because?: { key: string; value: string; label?: string }[];
  search_query?: string;
  attribution?: string;
  tool?: string;
  as_of?: string;
}

/** True when the ask is clearly “find/buy a product” even if Luna misfires. */
export function wantsProductSearch(text: string, intent?: string): boolean {
  if (intent === "product_search") return true;
  return /\b(need|want|find|buy|looking for|get me|show me)\b/i.test(text)
    && /\b(shirt|shirts|shoes|sneakers|dress|jeans|hoodie|jacket|charger|shampoo|sunscreen|headphones?|watch)\b/i.test(text);
}

export function searchShopping(query: string): Promise<ShoppingResult> {
  return apiPost<ShoppingResult>("/api/shopping/search", { query: query.slice(0, 120) });
}
