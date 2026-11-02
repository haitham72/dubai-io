// App-owned UI bots (Grok channel shape). Fine ontology lives in memory — not in the sidebar.
// Cursor-plan 2 Nov: Lifestyle · Career · Social · Household · Money · Travel (+ general).

export type DomainId =
  | "lifestyle"
  | "career"
  | "social"
  | "household"
  | "money"
  | "travel"
  | "general";

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
  | "gym"
  | "other";

export const DOMAIN_ORDER: DomainId[] = [
  "lifestyle",
  "household",
  "money",
  "travel",
  "career",
  "social",
  "general",
];

export const DOMAIN_LABEL: Record<DomainId, string> = {
  lifestyle: "Lifestyle",
  career: "Career",
  social: "Social",
  household: "Household",
  money: "Money",
  travel: "Travel",
  general: "General",
};

export const SERVICE_CATEGORIES: { id: ServiceCategoryId; label: string; domain: DomainId }[] = [
  { id: "laundry", label: "Laundry", domain: "lifestyle" },
  { id: "cleaning", label: "Cleaning", domain: "household" },
  { id: "ac", label: "AC repair", domain: "household" },
  { id: "carwash", label: "Car wash", domain: "travel" },
  { id: "pharmacy", label: "Pharmacy", domain: "money" },
  { id: "maid", label: "Maid hire", domain: "household" },
  { id: "grooming", label: "Pet grooming", domain: "lifestyle" },
  { id: "food", label: "Food & delivery", domain: "lifestyle" },
  { id: "hotels", label: "Hotels & stays", domain: "travel" },
  { id: "maintenance", label: "Home maintenance", domain: "household" },
  { id: "bills", label: "Bills & utilities", domain: "money" },
  { id: "schools", label: "Schools", domain: "household" },
  { id: "insurance", label: "Insurance", domain: "money" },
  { id: "transport", label: "Transport", domain: "travel" },
  { id: "gym", label: "Gym", domain: "lifestyle" },
];

type Rule = { domain: DomainId; category?: ServiceCategoryId; pattern: RegExp };

/** Keyword rules — first match wins. Civic bills → money (display/reminders; no fake pay). */
const RULES: Rule[] = [
  { domain: "money", category: "bills", pattern: /\b(dewa|salik|etisalat|du bill|utility|utilities|electricity|water bill|pay.*bills?)\b/i },
  { domain: "money", category: "insurance", pattern: /\b(insurance|hospital network|b\+|clinic|eligible hospital|ear pain)\b/i },
  { domain: "household", category: "ac", pattern: /\b(ac\b|a\/c|air ?cond|cooling)\b/i },
  { domain: "household", category: "maintenance", pattern: /\b(repair|plumber|electrician|maintenance|leak|broken)\b/i },
  { domain: "household", category: "schools", pattern: /\b(khda|school|nursery|kindergarten|tuition|year\s*[0-9]|british curriculum)\b/i },
  { domain: "household", category: "cleaning", pattern: /\b(maid|cleaning|cleaner|housekeep|guests?\s+at|flat ready)\b/i },
  { domain: "travel", category: "hotels", pattern: /\b(hotel|stay|check[- ]?in|airbnb)\b/i },
  { domain: "travel", category: "transport", pattern: /\b(near me|taxi|uber|careem|hala|dxb|airport|flight|lost.*bag|track your ride)\b/i },
  { domain: "lifestyle", category: "food", pattern: /\b(mamzar|beach|outing|deliver|talabat|noon now|order food|meal|restaurant|cafe|coffee)\b/i },
  { domain: "lifestyle", category: "laundry", pattern: /\b(laundry|press(ing)?|dry ?clean|shirt)\b/i },
  { domain: "lifestyle", category: "gym", pattern: /\b(gyms?|fitness first|membership renew|pilates|yoga class)\b/i },
  { domain: "lifestyle", category: "carwash", pattern: /\b(car ?wash|detailing)\b/i },
  { domain: "lifestyle", category: "grooming", pattern: /\b(groom|vet|pet)\b/i },
  { domain: "lifestyle", category: "pharmacy", pattern: /\b(pharmac|medicine|prescription)\b/i },
  { domain: "travel", category: "transport", pattern: /\b(parking|parkin|route|directions|map|trip|get around)\b/i },
  { domain: "career", pattern: /\b(email|gmail|outlook|calendar|meeting|slack|invoice|reimburs|visa|emirates id|job application)\b/i },
  { domain: "social", pattern: /\b(community|neighbour|neighbor|feed post|whatsapp group)\b/i },
];

export type DomainGuess = {
  domain: DomainId;
  category: ServiceCategoryId | null;
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
