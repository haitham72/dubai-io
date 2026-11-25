export type Provenance = "official" | "provider_confirmed" | "merchant_submitted" | "user_supplied" | "inferred" | "estimate" | "demo_fixture";
export interface Author { handle: string; display_name?: string; owner?: string }
export interface Post {
  id: string; text: string; author: Author; group_id?: string | null; group_name?: string;
  created_at?: string; as_of?: string; provenance?: Provenance | string;
  reactions?: number; reaction_count?: number; comments?: number; comment_count?: number;
  reacted?: boolean; bookmarked?: boolean; mine?: boolean; pinned?: boolean;
  media_label?: string; why?: string;
}
export interface Group {
  id: string; name: string; handle: string; description?: string; visibility: string;
  member_count?: number; members?: number; is_member?: boolean; provenance?: string; as_of?: string;
  my_role?: string | null; my_status?: string | null;
}
export interface Notification {
  id: string; kind?: string; type?: string; actor?: string; text?: string;
  is_read?: boolean; read?: boolean; created_at?: string; post_id?: string | null;
}
export interface Profile {
  handle: string; display_name?: string; bio?: string; area?: string;
  interests?: string[]; privacy?: string; provenance?: string; as_of?: string;
  mine?: boolean; owner?: string; age_band?: string;
}
export type Lane = "following" | "communities" | "discover";
