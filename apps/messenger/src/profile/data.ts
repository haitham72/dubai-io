// Fake data for the Profile and Settings modals. Owned by T11.
import { avatar, img } from "../ui";

export const me = {
  name: "Haitham",
  fullName: "Haitham Mohamed Ibrahim",
  handle: "@haitham",
  bio: "Building Messenger. Coffee, kite beach weekends and good design.",
  avatar: avatar(12),
  cover: img("photo-1512453979798-5ea266f8880c", 1400),
  email: "haitham@messenger.app",
  phone: "+971 50 123 4567",
  location: "Dubai, UAE",
  birthday: "Mar 14, 1990",
  language: "English",
  joined: "Member since Jan 2024",
};

export type Status = "online" | "away" | "busy" | "invisible";
export const statuses: { value: Status; label: string }[] = [
  { value: "online", label: "Online" },
  { value: "away", label: "Away" },
  { value: "busy", label: "Do not disturb" },
  { value: "invisible", label: "Invisible" },
];

export const plan = {
  name: "Messenger Pro",
  price: "AED 29 / month",
  renews: "Renews on Nov 4, 2026",
  usage: [
    { label: "AI messages", used: 1840, total: 3000, unit: "" },
    { label: "Image generations", used: 42, total: 100, unit: "" },
    { label: "Video generations", used: 6, total: 20, unit: "" },
    { label: "Research reports", used: 11, total: 30, unit: "" },
  ],
};

export const billing = [
  { id: "b1", date: "Oct 4, 2026", item: "Messenger Pro · monthly", amount: "AED 29.00", status: "Paid" },
  { id: "b2", date: "Sep 4, 2026", item: "Messenger Pro · monthly", amount: "AED 29.00", status: "Paid" },
  { id: "b3", date: "Aug 4, 2026", item: "Messenger Pro · monthly", amount: "AED 29.00", status: "Paid" },
  { id: "b4", date: "Jul 21, 2026", item: "Extra image credits · 50", amount: "AED 15.00", status: "Paid" },
];

export type DeviceKind = "laptop" | "phone" | "tablet" | "desktop";
export const devices: { id: string; name: string; kind: DeviceKind; detail: string; active: string; current?: boolean }[] = [
  { id: "d1", name: "MacBook Pro 16″", kind: "laptop", detail: "Chrome · Dubai, UAE", active: "Active now", current: true },
  { id: "d2", name: "iPhone 16 Pro", kind: "phone", detail: "Messenger for iOS · Dubai, UAE", active: "2 min ago" },
  { id: "d3", name: "iPad Air", kind: "tablet", detail: "Messenger for iPadOS · Abu Dhabi, UAE", active: "Yesterday" },
  { id: "d4", name: "Office iMac", kind: "desktop", detail: "Safari · Dubai Internet City", active: "3 days ago" },
];

export const storage = {
  used: 38.4,
  total: 100,
  categories: [
    { id: "photos", label: "Photos", size: 16.2, tone: "blue" },
    { id: "videos", label: "Videos", size: 11.8, tone: "purple" },
    { id: "docs", label: "Documents", size: 5.1, tone: "success" },
    { id: "voice", label: "Voice notes", size: 2.6, tone: "warning" },
    { id: "other", label: "Other", size: 2.7, tone: "muted" },
  ] as const,
};

export const apps = [
  { id: "drive", name: "Google Drive", detail: "Attach files from your Drive", connected: true },
  { id: "icloud", name: "iCloud", detail: "Photos and documents", connected: true },
  { id: "outlook", name: "Outlook", detail: "Mail and calendar sync", connected: false },
  { id: "telegram", name: "Telegram", detail: "Import chats and contacts", connected: false },
  { id: "spotify", name: "Spotify", detail: "Share what you're listening to", connected: true },
  { id: "notion", name: "Notion", detail: "Send research reports to pages", connected: false },
];

/** Toggle settings, grouped by tab. Values live in modal state while the app runs. */
export const toggleGroups: Record<string, { id: string; label: string; detail: string; on: boolean }[]> = {
  notifications: [
    { id: "n-msg", label: "Messages", detail: "New messages from chats and groups", on: true },
    { id: "n-mention", label: "Mentions only in groups", detail: "Mute group chatter except @mentions", on: false },
    { id: "n-updates", label: "Messenger Updates", detail: "When images, videos and research are ready", on: true },
    { id: "n-calendar", label: "Calendar reminders", detail: "15 minutes before each event", on: true },
    { id: "n-sound", label: "Sounds", detail: "Play a sound for incoming messages", on: true },
    { id: "n-preview", label: "Message previews", detail: "Show message text in notifications", on: false },
  ],
  privacy: [
    { id: "p-seen", label: "Read receipts", detail: "Let people see when you've read messages", on: true },
    { id: "p-online", label: "Show online status", detail: "Others can see when you're online", on: true },
    { id: "p-photo", label: "Profile photo visible to everyone", detail: "Otherwise contacts only", on: false },
    { id: "p-lock", label: "App lock", detail: "Require Face ID after 5 minutes", on: true },
    { id: "p-analytics", label: "Share usage analytics", detail: "Anonymous, helps improve Messenger", on: false },
  ],
  ai: [
    { id: "ai-web", label: "Web search", detail: "Let Messenger AI search the web for fresh answers", on: true },
    { id: "ai-memory", label: "Memory", detail: "Remember preferences across conversations", on: true },
    { id: "ai-chat", label: "@messenger in chats", detail: "Ask Messenger from any conversation", on: true },
    { id: "ai-images", label: "Image generation", detail: "Allow creating images from prompts", on: true },
    { id: "ai-actions", label: "Ask before actions", detail: "Confirm before sending mail or booking", on: true },
  ],
};

export const responseStyles = ["Concise", "Balanced", "Detailed"] as const;

export const sessions = [
  { label: "Password", value: "Last changed 3 months ago", action: "Change" },
  { label: "Two-factor authentication", value: "On · Authenticator app", action: "Manage" },
  { label: "Passkeys", value: "2 passkeys saved", action: "Manage" },
  { label: "Recovery email", value: "h.ibrahim@gmail.com", action: "Edit" },
];
