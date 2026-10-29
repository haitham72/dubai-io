// Product domains replace Grok-style “bot channels”.
// A domain is where a task thread lives in the sidebar; a service category is the job type under Services.

export type DomainId = "household" | "places" | "services" | "work" | "general";

export type ServiceCategoryId =
  | "laundry"
  | "cleaning"
  | "ac"
  | "carwash"
  | "pharmacy"
  | "maid"
  | "grooming"
  | "food"
  | "hotels"
  | "maintenance"
  | "bills"
  | "schools"
  | "insurance"
  | "transport"
  | "other";

export const DOMAIN_ORDER: DomainId[] = ["household", "places", "services", "work", "general"];

export const DOMAIN_LABEL: Record<DomainId, string> = {
  household: "Household",
  places: "Places & trips",
  services: "Services",
  work: "Work & admin",
  general: "General",
};

export const SERVICE_CATEGORIES: { id: ServiceCategoryId; label: string; domain: DomainId }[] = [
  { id: "laundry", label: "Laundry", domain: "services" },
  { id: "cleaning", label: "Cleaning", domain: "services" },
  { id: "ac", label: "AC repair", domain: "household" },
  { id: "carwash", label: "Car wash", domain: "services" },
  { id: "pharmacy", label: "Pharmacy", domain: "services" },
  { id: "maid", label: "Maid hire", domain: "services" },
  { id: "grooming", label: "Pet grooming", domain: "services" },
  { id: "food", label: "Food & delivery", domain: "services" },
  { id: "hotels", label: "Hotels & stays", domain: "household" },
  { id: "maintenance", label: "Home maintenance", domain: "household" },
  { id: "bills", label: "Bills & utilities", domain: "household" },
  { id: "schools", label: "Schools", domain: "household" },
  { id: "insurance", label: "Insurance", domain: "household" },
  { id: "transport", label: "Transport", domain: "places" },
  { id: "other", label: "Something else", domain: "general" },
];

type Rule = { domain: DomainId; category?: ServiceCategoryId; pattern: RegExp };

/** Keyword rules — first match wins. Keep DEWA/Salik/gov as household display/reminders only (no execution). */
const RULES: Rule[] = [
  { domain: "household", category: "bills", pattern: /\b(dewa|salik|etisalat|du bill|utility|utilities|electricity|water bill)\b/i },
  { domain: "household", category: "ac", pattern: /\b(ac\b|a\/c|air ?cond|cooling)\b/i },
  { domain: "household", category: "maintenance", pattern: /\b(repair|plumber|electrician|maintenance|leak|broken)\b/i },
  { domain: "household", category: "hotels", pattern: /\b(hotel|stay|check[- ]?in|airbnb)\b/i },
  { domain: "household", category: "schools", pattern: /\b(khda|school|nursery|kindergarten|tuition)\b/i },
  { domain: "household", category: "insurance", pattern: /\b(insurance|hospital network|b\+|clinic|eligible hospital)\b/i },
  { domain: "household", category: "cleaning", pattern: /\b(maid|cleaning|cleaner|housekeep)\b/i },
  { domain: "places", category: "transport", pattern: /\b(near me|best place|restaurant|cafe|coffee|trip|outing|mamzar|beach|parking|parkin|route|directions|map|taxi|uber|careem|dxb|airport|flight)\b/i },
  { domain: "services", category: "laundry", pattern: /\b(laundry|press(ing)?|dry ?clean|shirt)\b/i },
  { domain: "services", category: "carwash", pattern: /\b(car ?wash|detailing)\b/i },
  { domain: "services", category: "pharmacy", pattern: /\b(pharmac|medicine|prescription)\b/i },
  { domain: "services", category: "grooming", pattern: /\b(groom|vet|pet)\b/i },
  { domain: "services", category: "food", pattern: /\b(deliver|talabat|noon now|order food|meal)\b/i },
  { domain: "work", pattern: /\b(email|gmail|outlook|calendar|meeting|slack|invoice|reimburs|visa|emirates id)\b/i },
];

export type DomainGuess = {
  domain: DomainId;
  category: ServiceCategoryId | null;
  /** How the guess was made — never claims more certainty than keyword match. */
  provenance: "keyword" | "default";
};

export function classifyDomain(text: string): DomainGuess {
  const q = text.trim();
  if (!q) return { domain: "general", category: null, provenance: "default" };
  for (const rule of RULES) {
    if (rule.pattern.test(q)) {
      return { domain: rule.domain, category: rule.category ?? null, provenance: "keyword" };
    }
  }
  return { domain: "general", category: null, provenance: "default" };
}

export function groupByDomain<T extends { domain: DomainId }>(
  items: T[],
): { domain: DomainId; label: string; items: T[] }[] {
  const buckets = new Map<DomainId, T[]>();
  for (const id of DOMAIN_ORDER) buckets.set(id, []);
  for (const item of items) {
    (buckets.get(item.domain) ?? buckets.get("general")!).push(item);
  }
  return DOMAIN_ORDER
    .map((domain) => ({ domain, label: DOMAIN_LABEL[domain], items: buckets.get(domain) ?? [] }))
    .filter((g) => g.items.length > 0);
}
