import type {
  ActionCard,
  ChatMessage,
  LifeDrawerItem,
  RepairPing,
  TodayRail,
} from "./types";

/** Synthetic Karim Haddad. Every rendered fixture carries a Demo data pill. */
export const DEMO_OWNER_ID = "karim";
export const DEMO_AS_OF = "2026-11-23";

export const karimToday = {
  greeting: "Good morning, Karim",
  placeLine: "Dubai · Monday, 23 Nov",
  recapTitle: "Your Weekly Recap",
  recapBody: "The top updates, new releases, and what's next in your Dubai-io world.",
};

export const todayRails: TodayRail[] = [
  {
    id: "gaming",
    title: "Gaming & Hardware",
    cards: [
      {
        id: "gta",
        title: "GTA VI — An all-new open world experience.",
        eyebrow: "AED 299 · estimate",
        because: "you told me you track open-world releases",
        tone: "gaming",
        demo: true,
        provenance: "estimate",
        asOf: DEMO_AS_OF,
      },
      {
        id: "ps5",
        title: "PS5 bundle on a marble pedestal.",
        eyebrow: "Hardware",
        because: "you saved a controller note last week",
        tone: "gaming",
        demo: true,
        provenance: "demo_fixture",
        asOf: DEMO_AS_OF,
      },
    ],
  },
  {
    id: "dev",
    title: "Developer & AI Systems",
    cards: [
      {
        id: "ide",
        title: "ide-companio — Your AI coding companion.",
        eyebrow: "Project",
        because: "you draft agent tools in the evening",
        tone: "projects",
        demo: true,
        provenance: "demo_fixture",
        asOf: DEMO_AS_OF,
      },
      {
        id: "hermes",
        title: "Hermes Agent — a metallic research sketch.",
        eyebrow: "Learning",
        because: "you asked for a second coding agent",
        tone: "learning",
        demo: true,
        provenance: "demo_fixture",
        asOf: DEMO_AS_OF,
      },
    ],
  },
];

export const demoThread: ChatMessage[] = [
  {
    id: "u-format",
    role: "user",
    text: "Can you improve the formatting in the last report? The sections felt a bit dense.",
    at: "10:24 AM",
    ingested: false,
    demo: true,
  },
  {
    id: "a-format",
    role: "assistant",
    text: "Got it. I've logged your feedback and updated my report style to be more structured and scannable.",
    at: "10:25 AM",
    ingested: false,
    demo: true,
  },
];

export const demoRepair: RepairPing = {
  id: "repair-gaming",
  title: "Proactive Ping · Memory Repair",
  body: "I'm sorry I missed your gaming interests earlier. I've updated your permanent memory profile to include gaming (GTA, hardware, and releases).",
  demo: true,
  provenance: "demo_fixture",
  asOf: DEMO_AS_OF,
};

export const demoAction: ActionCard = {
  id: "gta-news",
  title: "GTA 6 PC timeline update",
  subtitle: "Shared News DB · 2h ago",
  demo: true,
  provenance: "demo_fixture",
  asOf: DEMO_AS_OF,
};

export const lifeThemes: LifeDrawerItem[] = [
  { id: "today", label: "Today", detail: "6 active items" },
  { id: "career", label: "Career & Projects", detail: "12 verified items" },
  { id: "people", label: "People & Family", detail: "8 verified contacts" },
  { id: "gaming", label: "Gaming & Hardware", detail: "4 active tracks" },
  { id: "travel", label: "Travel & Places", detail: "3 itineraries" },
  { id: "home", label: "Home & Money", detail: "5 financial anchors" },
];

export const threadHistory: LifeDrawerItem[] = [
  { id: "h1", label: "Report formatting feedback", detail: "Today" },
  { id: "h2", label: "GTA 6 PC timeline", detail: "Today" },
  { id: "h3", label: "Istanbul trip planning", detail: "Mon" },
  { id: "h4", label: "Job application update", detail: "Sun" },
  { id: "h5", label: "Gaming setup recommendation", detail: "Fri" },
];

export const OFFLINE_ASSISTANT_REPLY =
  "I can't reach the memory service from this phone. This reply is demo data and was not written to Temporal Memory.";
