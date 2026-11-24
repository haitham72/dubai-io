import type { Group, Notification, Post, Profile } from "./types";

const asOf = "2026-11-23T00:00:00Z";
export const seedPosts: Post[] = [
  {
    id: "demo-1", text: "Morning walk along the marina — the light at 7am makes the whole route feel new again. Anyone else doing the Saturday loop?",
    author: { handle: "sara_m", display_name: "Sara M." }, group_id: "g-walks", group_name: "Weekend Walks",
    created_at: asOf, as_of: asOf, provenance: "demo_fixture", reactions: 12, comments: 4,
    media_label: "Marina promenade at sunrise (demo image)", why: "You follow Sara and joined Weekend Walks.",
  },
  {
    id: "demo-2", text: "Found a small book-swap shelf in JLT cluster D. Left two novels, took one. Lovely idea — should we start one per cluster?",
    author: { handle: "omar_k", display_name: "Omar K." }, group_id: "g-books", group_name: "Book Swap Circle",
    created_at: asOf, as_of: asOf, provenance: "demo_fixture", reactions: 8, comments: 6,
    why: "Matches an interest you saved: reading.",
  },
  {
    id: "demo-3", text: "Reminder: community garden volunteer hour is Friday 8am. Bring gloves if you have them; tools are provided.",
    author: { handle: "layla_a", display_name: "Layla A." }, group_id: "g-garden", group_name: "Community Garden",
    created_at: asOf, as_of: asOf, provenance: "demo_fixture", reactions: 5, comments: 2, pinned: true,
    why: "Pinned in a community you joined.",
  },
];

export const seedGroups: Group[] = [
  { id: "g-walks", name: "Weekend Walks", handle: "weekend-walks", description: "Easy-paced Saturday walks around the city.", visibility: "public", member_count: 128, is_member: true, provenance: "demo_fixture", as_of: asOf },
  { id: "g-books", name: "Book Swap Circle", handle: "book-swap", description: "Swap, lend and discuss books locally.", visibility: "public", member_count: 86, is_member: true, provenance: "demo_fixture", as_of: asOf },
  { id: "g-garden", name: "Community Garden", handle: "community-garden", description: "Volunteer hours and harvest sharing.", visibility: "public", member_count: 54, is_member: false, provenance: "demo_fixture", as_of: asOf },
  { id: "g-neighbours", name: "Neighbours Circle", handle: "neighbours", description: "Private circle for verified neighbours. Membership by invite.", visibility: "private", member_count: 32, is_member: false, provenance: "demo_fixture", as_of: asOf },
];

export const seedNotifications: Notification[] = [
  { id: "n1", kind: "reply", actor: "omar_k", text: "replied to your post", is_read: false, created_at: asOf },
  { id: "n2", kind: "mention", actor: "sara_m", text: "mentioned you in Weekend Walks", is_read: false, created_at: asOf },
  { id: "n3", kind: "group", actor: "layla_a", text: "pinned a post in Community Garden", is_read: true, created_at: asOf },
];

export const seedProfile: Profile = {
  handle: "you", display_name: "You", bio: "Preview profile for founder review.",
  area: "Dubai", interests: ["reading", "walking"], privacy: "public",
  provenance: "demo_fixture", as_of: asOf,
};

export const followedHandles = ["sara_m", "omar_k"];
export const joinedGroupIds = ["g-walks", "g-books", "g-garden"];
