// Fake History timeline: everything Mirsal did for the user. Owned by T11.
import { img } from "../../ui";

export type Kind = "image" | "flight" | "research" | "email" | "weather" | "video";
export type Day = "Today" | "Yesterday" | "This week" | "Earlier";

export interface Entry {
  id: string;
  kind: Kind;
  day: Day;
  time: string;
  title: string;
  summary: string;
  source: string; // where it was asked: "AI Chat", "Chat with Arif", …
  image?: string;
  prompt?: string;
  route?: { from: string; to: string; date: string; price: string; airline: string; stops: string };
  doc?: { pages: number; insights: number; sources: number; findings: string[] };
  mail?: { to: string; subject: string; body: string };
  weather?: { city: string; temp: number; cond: string; hi: number; lo: number };
}

export const entries: Entry[] = [
  { id: "h1", kind: "image", day: "Today", time: "3:12 PM", title: "Dubai beach at golden hour", summary: "Instagram post visual, 4:5", source: "AI Chat",
    image: img("photo-1512453979798-5ea266f8880c", 1200), prompt: "Dubai skyline from the beach at golden hour, warm light, Instagram 4:5" },
  { id: "h2", kind: "flight", day: "Today", time: "1:40 PM", title: "Flights DXB → LHR", summary: "3 options from AED 2,180 · 11 Dec", source: "AI Chat",
    route: { from: "DXB", to: "LHR", date: "Thu, 11 Dec", price: "AED 2,180", airline: "Emirates EK 1", stops: "Non-stop · 7h 40m" } },
  { id: "h3", kind: "weather", day: "Today", time: "9:05 AM", title: "Weekend weather in Dubai", summary: "Sunny, 37° / 28° · light breeze", source: "Chat with Arif",
    weather: { city: "Dubai", temp: 34, cond: "Sunny", hi: 37, lo: 28 } },
  { id: "h4", kind: "research", day: "Today", time: "8:30 AM", title: "UAE AI market trends 2026", summary: "5 key insights · 14 sources", source: "Research",
    image: img("photo-1555400038-63f5ba517a47", 1200),
    doc: { pages: 6, insights: 5, sources: 14, findings: [
      "Sovereign AI and cloud investment keep growing through 2026.",
      "Arabic-first models close most of the gap with English benchmarks.",
      "Enterprise adoption concentrates in government, banking and aviation.",
      "Talent demand outpaces supply; upskilling programs triple.",
      "Agentic workflows move from pilots to production.",
    ] } },
  { id: "h5", kind: "video", day: "Yesterday", time: "7:48 PM", title: "Mirsal promo reel", summary: "30s vertical clip with music", source: "AI Chat",
    image: img("photo-1513635269975-59663e0ac1ad", 1200), prompt: "Short upbeat promo reel for the Mirsal app" },
  { id: "h6", kind: "email", day: "Yesterday", time: "5:15 PM", title: "Follow-up to Sara about the dinner", summary: "Draft ready · sent at 5:20 PM", source: "Mail",
    mail: { to: "Sara Ali", subject: "Dinner on Friday 🎉", body: "Hi Sara,\n\nCongrats again on the promotion! I booked a table at Il Borro for Friday at 8. Let me know if that works.\n\nHaitham" } },
  { id: "h7", kind: "image", day: "Yesterday", time: "11:02 AM", title: "Kite Beach weekend poster", summary: "Group invite for Travel Buddies", source: "Chat with Travel Buddies",
    image: img("photo-1507525428034-b723cf961d3e", 1200), prompt: "Bright kite beach poster, turquoise sea, bold title 'Weekend at Kite Beach'" },
  { id: "h8", kind: "flight", day: "This week", time: "Mon", title: "Flights JED → DXB", summary: "Best price AED 1,240 · 12 Dec", source: "Chat with Omar",
    route: { from: "JED", to: "DXB", date: "Sat, 12 Dec", price: "AED 1,240", airline: "Saudia SV 542", stops: "Non-stop · 2h 20m" } },
  { id: "h9", kind: "research", day: "This week", time: "Mon", title: "RAG vs fine-tuning", summary: "When to use which · 6 insights", source: "Research",
    doc: { pages: 4, insights: 6, sources: 9, findings: [
      "RAG wins when facts change often or must be cited.",
      "Fine-tuning wins for tone, format and narrow skills.",
      "Most teams combine both: a tuned model reading retrieved context.",
    ] } },
  { id: "h10", kind: "weather", day: "This week", time: "Sun", title: "Abu Dhabi weekend forecast", summary: "Hot and clear, 39° / 29°", source: "AI Chat",
    weather: { city: "Abu Dhabi", temp: 36, cond: "Clear", hi: 39, lo: 29 } },
  { id: "h11", kind: "image", day: "This week", time: "Sun", title: "Family dinner table", summary: "Edited photo for the family group", source: "Chat with Family",
    image: img("photo-1511895426328-dc8714191300", 1200), prompt: "Warm family dinner photo, soft evening light" },
  { id: "h12", kind: "email", day: "Earlier", time: "Sep 28", title: "Reply to Emirates about seat change", summary: "Sent · confirmation received", source: "Mail",
    mail: { to: "Emirates Support", subject: "Seat change for booking EK7Q2M", body: "Hello,\n\nCould you move me to a window seat on EK 1 on 11 December? Thank you.\n\nHaitham Mohamed Ibrahim" } },
  { id: "h13", kind: "image", day: "Earlier", time: "Sep 26", title: "Bali villa mood board", summary: "4 images for trip planning", source: "Chat with Travel Buddies",
    image: img("photo-1537996194471-e657df975ab4", 1200), prompt: "Bali villa with infinity pool and rice terraces" },
  { id: "h14", kind: "research", day: "Earlier", time: "Sep 24", title: "Sovereign cloud in the GCC", summary: "5 key insights · 11 sources", source: "Research",
    doc: { pages: 5, insights: 5, sources: 11, findings: [
      "Data-residency rules push hyperscalers to open in-country regions.",
      "Local providers compete on compliance and Arabic support.",
    ] } },
];

export const filters = [
  { id: "all", label: "All" },
  { id: "image", label: "Images" },
  { id: "flight", label: "Flights" },
  { id: "research", label: "Research" },
  { id: "email", label: "Email" },
  { id: "weather", label: "Weather" },
] as const;
export type Filter = (typeof filters)[number]["id"];

export const days: Day[] = ["Today", "Yesterday", "This week", "Earlier"];

export const stats = [
  { id: "images", label: "Images generated", value: "128", delta: "+12 this week" },
  { id: "flights", label: "Flights searched", value: "36", delta: "+4 this week" },
  { id: "research", label: "Research reports", value: "24", delta: "+3 this week" },
  { id: "hours", label: "Hours saved", value: "41", delta: "≈ 6 this week" },
];
