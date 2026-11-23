// Files fake data. Photos verified: curl → 200 on 2026-10-04.
import { avatar } from "../../ui";

export interface FileItem {
  id: string;
  name: string;
  type: "image" | "video" | "document" | "pdf" | "audio" | "folder";
  size: string;
  modified: string;
  thumbnail?: string;
  sharedBy?: string;
  starred?: boolean;
  group?: FileGroup;
}

export type FileGroup = "Today" | "Yesterday" | "This week" | "Earlier";
export const fileGroups: FileGroup[] = ["Today", "Yesterday", "This week", "Earlier"];

export interface SharedItem {
  id: string;
  file: FileItem;
  sharer: string;
  sharerAvatar: string;
  permission: "view" | "edit";
  sharedAt: string;
}

export const categories = [
  { id: "all", label: "All Files", count: 128 },
  { id: "recent", label: "Recents", count: 24 },
  { id: "shared", label: "Shared", count: 7 },
  { id: "starred", label: "Starred", count: 5 },
  { id: "trash", label: "Trash", count: 3 },
];

export const typeCategories = [
  { id: "images", label: "Images", icon: "Image", count: 42 },
  { id: "generated", label: "Generated", icon: "Sparkles", count: 0 },
  { id: "videos", label: "Videos", icon: "Film", count: 18 },
  { id: "documents", label: "Documents", icon: "FileText", count: 35 },
  { id: "pdfs", label: "PDFs", icon: "FileType2", count: 12 },
  { id: "audio", label: "Audio", icon: "Music", count: 8 },
  { id: "folders", label: "Folders", icon: "Folder", count: 13 },
];

export const cloudSources = [
  { name: "iCloud Drive", used: 8.4, total: 15, color: "var(--blue)" },
  { name: "Google Drive", used: 12.2, total: 15, color: "var(--success)" },
  { name: "Local Files", used: 45.7, total: 100, color: "var(--text-2)" },
];

const recent: Omit<FileItem, "group">[] = [
  { id: "f13", name: "Messenger pitch deck", type: "folder", size: "8 items", modified: "10 min ago" },
  { id: "f2", name: "Project proposal.pdf", type: "pdf", size: "1.8 MB", modified: "15 min ago" },
  { id: "f4", name: "Budget 2025.xlsx", type: "document", size: "340 KB", modified: "2 hours ago" },
  { id: "f5", name: "Meeting notes.docx", type: "document", size: "128 KB", modified: "3 hours ago" },
  { id: "f15", name: "Voice memo · Sara.m4a", type: "audio", size: "3.4 MB", modified: "5 hours ago" },
  { id: "f7", name: "Invoice October.pdf", type: "pdf", size: "560 KB", modified: "Yesterday" },
  { id: "f16", name: "Bali itinerary", type: "folder", size: "14 items", modified: "Yesterday" },
  { id: "f17", name: "Emirates e-ticket EK1.pdf", type: "pdf", size: "212 KB", modified: "Yesterday" },
  { id: "f8", name: "Podcast ep.42.mp3", type: "audio", size: "84 MB", modified: "2 days ago" },
  { id: "f9", name: "Screenshots", type: "folder", size: "12 items", modified: "3 days ago" },
  { id: "f10", name: "Contract draft.pdf", type: "pdf", size: "920 KB", modified: "4 days ago" },
  { id: "f11", name: "Logo assets.zip", type: "document", size: "15 MB", modified: "5 days ago" },
  { id: "f20", name: "Tax documents 2025", type: "folder", size: "23 items", modified: "Sep 18" },
  { id: "f21", name: "Research · UAE AI market.pdf", type: "pdf", size: "2.6 MB", modified: "Sep 12" },
  { id: "f22", name: "Gaming night clips", type: "folder", size: "6 items", modified: "Aug 30" },
];

/** "2 min ago" → Today, "Yesterday", "N days ago" → This week, anything older → Earlier. */
function groupOf(modified: string): FileGroup {
  if (/min|hour/.test(modified)) return "Today";
  if (modified === "Yesterday") return "Yesterday";
  if (/days ago/.test(modified)) return "This week";
  return "Earlier";
}

export const recentFiles: FileItem[] = recent.map((f) => ({ ...f, group: groupOf(f.modified) }));

export const sharedWithMe: SharedItem[] = [
  {
    id: "s1",
    file: { id: "sf1", name: "Q3 Report.pdf", type: "pdf", size: "2.4 MB", modified: "1 hour ago" },
    sharer: "Sara Ali", sharerAvatar: avatar(47), permission: "edit", sharedAt: "1h ago",
  },
  {
    id: "s2",
    file: { id: "sf2", name: "Team offsite notes.docx", type: "document", size: "96 KB", modified: "3 hours ago" },
    sharer: "Mazen", sharerAvatar: avatar(53), permission: "view", sharedAt: "3h ago",
  },
  {
    id: "s3",
    file: { id: "sf3", name: "Design mockups.zip", type: "document", size: "48 MB", modified: "Yesterday" },
    sharer: "Lina", sharerAvatar: avatar(44), permission: "edit", sharedAt: "Yesterday",
  },
  {
    id: "s4",
    file: { id: "sf4", name: "Flight itinerary.pdf", type: "pdf", size: "340 KB", modified: "2 days ago" },
    sharer: "Omar", sharerAvatar: avatar(59), permission: "view", sharedAt: "2 days ago",
  },
];


export function fileTypeIconName(type: FileItem["type"]): string {
  switch (type) {
    case "image": return "Image";
    case "video": return "Film";
    case "audio": return "Music";
    case "pdf": return "FileType2";
    case "document": return "FileText";
    case "folder": return "Folder";
  }
}
