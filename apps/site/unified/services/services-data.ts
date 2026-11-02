/** Demo catalog for the unified Services screen (provenance: demo_fixture). */

export type ServiceCategory = "home" | "laundry" | "pets" | "car" | "bills" | "government";

export type ServiceKind = "provider" | "portal";

export type DemoService = {
  id: string;
  kind: ServiceKind;
  name: string;
  description: string;
  area: string;
  rating: number;
  reviewCount: number;
  priceFromAed: number | null;
  priceUnit?: string;
  image?: string;
  categories: ServiceCategory[];
  provenance: "demo_fixture";
  portalUrl?: string;
};

export type RequestStatusTone = "waiting" | "review" | "draft";

export type DemoRequest = {
  id: string;
  title: string;
  at: string;
  status: string;
  tone: RequestStatusTone;
  provenance: "demo_fixture";
};

export const DEMO_SERVICES: DemoService[] = [
  {
    id: "marinaexpress",
    kind: "provider",
    name: "Marina Express Laundry",
    description: "Wash, dry and fold. Pickup and delivery in Dubai Marina.",
    area: "Dubai Marina",
    rating: 4.7,
    reviewCount: 320,
    priceFromAed: 6,
    priceUnit: "per shirt",
    image: "/images/media/laundry.jpg",
    categories: ["laundry"],
    provenance: "demo_fixture",
  },
  {
    id: "paws-jlt",
    kind: "provider",
    name: "Paws Grooming JLT",
    description: "Full grooming, bath and nail trim. Mobile van at your building.",
    area: "JLT",
    rating: 4.8,
    reviewCount: 156,
    priceFromAed: 80,
    priceUnit: "small dog",
    image: "/images/media/pets.jpg",
    categories: ["pets"],
    provenance: "demo_fixture",
  },
  {
    id: "quickfix-ac",
    kind: "provider",
    name: "QuickFix AC Repair",
    description: "AC servicing, repair and deep cleaning. Licensed technicians.",
    area: "Dubai",
    rating: 4.6,
    reviewCount: 412,
    priceFromAed: 120,
    priceUnit: "call-out",
    image: "/images/media/ac.jpg",
    categories: ["home"],
    provenance: "demo_fixture",
  },
  {
    id: "nest-clean",
    kind: "provider",
    name: "Home Cleaning",
    description: "Professional home cleaning by trained staff. Materials included.",
    area: "Dubai Marina",
    rating: 4.5,
    reviewCount: 89,
    priceFromAed: 35,
    priceUnit: "per hour",
    image: "/images/media/home-green.jpg",
    categories: ["home"],
    provenance: "demo_fixture",
  },
  {
    id: "dewa-bill",
    kind: "portal",
    name: "DEWA bill",
    description: "Open the official portal to view and pay your DEWA bill.",
    area: "Official portal",
    rating: 0,
    reviewCount: 0,
    priceFromAed: null,
    categories: ["bills", "government"],
    provenance: "demo_fixture",
    portalUrl: "https://www.dewa.gov.ae/",
  },
  {
    id: "car-service",
    kind: "provider",
    name: "Car Service & Repair",
    description: "Servicing, diagnostics and repairs for all makes.",
    area: "Al Quoz",
    rating: 4.4,
    reviewCount: 203,
    priceFromAed: 250,
    priceUnit: "service",
    image: "/images/media/home.jpg",
    categories: ["car"],
    provenance: "demo_fixture",
  },
];

export const DEMO_REQUESTS: DemoRequest[] = [
  { id: "r1", title: "Laundry pickup today, 18:30", at: "2h ago", status: "Waiting for the shop", tone: "waiting", provenance: "demo_fixture" },
  { id: "r2", title: "AC repair quote sent", at: "Yesterday", status: "In review", tone: "review", provenance: "demo_fixture" },
  { id: "r3", title: "Dog grooming Fri 10:00", at: "Draft", status: "Draft", tone: "draft", provenance: "demo_fixture" },
  { id: "r4", title: "Home clean Sat 09:00", at: "Draft", status: "Draft", tone: "draft", provenance: "demo_fixture" },
];

export type CategoryChip = "all" | ServiceCategory;

export const CATEGORY_CHIPS: { id: CategoryChip; label: string }[] = [
  { id: "all", label: "All" },
  { id: "home", label: "Home" },
  { id: "laundry", label: "Laundry" },
  { id: "pets", label: "Pets" },
  { id: "car", label: "Car" },
  { id: "bills", label: "Bills" },
  { id: "government", label: "Government" },
];

export function filterServices(
  services: DemoService[],
  query: string,
  category: CategoryChip,
): DemoService[] {
  const q = query.trim().toLowerCase();
  return services.filter((s) => {
    if (category !== "all" && !s.categories.includes(category)) return false;
    if (!q) return true;
    const hay = `${s.name} ${s.description} ${s.area} ${s.categories.join(" ")}`.toLowerCase();
    return hay.includes(q);
  });
}
