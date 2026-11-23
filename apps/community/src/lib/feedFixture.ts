/** Staged Feed v2 copy from the v3 frames. Synthetic names. Photos are stock, credited in public/demo/CREDITS.md. */

export interface FeedReply {
  name: string;
  text: string;
  estimate?: boolean;
  source?: string;
  votes?: number;
}

export interface FeedCard {
  id: string;
  title: string;
  text: string;
  time_label: string;
  votes: number;
  comments: number;
  provenance: "demo_fixture" | "user_supplied";
  author: { handle: string; display_name: string; avatar: string };
  community: { name: string; members: string; image: string; blurb?: string };
  media_url?: string;
  reply?: FeedReply;
  followed?: boolean;
}

export const jlt = {
  name: "JLT Residents",
  members: "12k members",
  blurb: "Life, living and everything JLT.",
  image: "/demo/jlt.jpg",
};

export const phonePosts: FeedCard[] = [
  {
    id: "nursery",
    title: "Which nursery near Cluster D has space for January?",
    text: "We're moving to JLT next month and looking for a good nursery (ideally near Cluster D). Any recommendations from parents here? Waiting lists seem long everywhere...",
    time_label: "2h",
    votes: 24,
    comments: 18,
    provenance: "demo_fixture",
    followed: true,
    author: { handle: "sara_k", display_name: "Sara Khalid", avatar: "/demo/sara.jpg" },
    community: jlt,
  },
  {
    id: "power",
    title: "Power cut in Cluster X again? DEWA app says nothing",
    text: "Third time this month. Power just went off in Cluster X about 20 minutes ago. DEWA app shows no outages. Anyone else facing this or know what's going on?",
    time_label: "5h",
    votes: 37,
    comments: 42,
    provenance: "demo_fixture",
    followed: true,
    author: { handle: "omarh", display_name: "Omar Hassan", avatar: "/demo/omar.jpg" },
    community: jlt,
  },
  {
    id: "cleanup",
    title: "Saturday cleanup at the lake, who's in?",
    text: "Planning a small community cleanup around JLT lake this Saturday morning. Gloves and bags will be provided. All are welcome — let's keep our community beautiful!",
    time_label: "8h",
    votes: 56,
    comments: 16,
    provenance: "demo_fixture",
    author: { handle: "leila_m", display_name: "Leila Mansour", avatar: "/demo/leila.jpg" },
    community: jlt,
  },
];

export const desktopPosts: FeedCard[] = [
  phonePosts[0],
  {
    id: "taxi",
    title: "Best way from DXB Terminal 1 to Dubai Marina at 1am?",
    text: "I'll be landing at Terminal 1 around 1am and need to get to Dubai Marina. What's the most reliable and safe option at that hour?",
    time_label: "5h",
    votes: 37,
    comments: 42,
    provenance: "demo_fixture",
    author: { handle: "omarh", display_name: "Omar Hassan", avatar: "/demo/omar.jpg" },
    community: { name: "Dubai Q&A", members: "26k members", image: "/demo/skyline.jpg" },
    reply: {
      name: "Dubai-io",
      text: "Metro is closed by then. Taxi from the T1 rank or a ride app are the most reliable options. Taxi fare is about AED 110–130.",
      estimate: true,
      source: "RTA taxi fares, as of Oct 2026",
      votes: 42,
    },
  },
  {
    id: "ikea",
    title: "Ikea dining table (6 seats) – good condition",
    text: "Selling a 6-seater Ikea dining table, lightly used, good condition. Located in JLT. DM if interested.",
    time_label: "8h",
    votes: 15,
    comments: 7,
    provenance: "demo_fixture",
    author: { handle: "leila_m", display_name: "Leila Mansour", avatar: "/demo/leila.jpg" },
    community: { name: "Dubai Classifieds", members: "18k members", image: "/demo/phone.jpg" },
  },
];

export const suggested = [
  { name: "Dubai Q&A", members: "26k members", blurb: "Ask questions, get local answers.", image: "/demo/skyline.jpg" },
  { name: "JLT Residents", members: "12k members", blurb: "Life, living and everything JLT.", image: "/demo/jlt.jpg" },
  { name: "Dubai Classifieds", members: "18k members", blurb: "Buy, sell, give away in Dubai.", image: "/demo/phone.jpg" },
  { name: "Dubai Parents", members: "9k members", blurb: "Support for families in Dubai.", image: "/demo/home.jpg" },
  { name: "Dubai Professionals", members: "14k members", blurb: "Careers, skills and networking.", image: "/demo/office.jpg" },
];
