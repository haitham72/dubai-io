import AsyncStorage from "@react-native-async-storage/async-storage";
import { normalizeCommunityUrl } from "../config/url";

const STORAGE_KEY = "dubai-io.community.mobile.urlOverride.v1";

export async function loadUrlOverride(): Promise<string | null> {
  try {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const normalized = normalizeCommunityUrl(raw);
    return normalized.ok ? normalized.url : null;
  } catch {
    return null;
  }
}

export async function saveUrlOverride(url: string): Promise<void> {
  const normalized = normalizeCommunityUrl(url);
  if (!normalized.ok) {
    throw new Error(normalized.error);
  }
  await AsyncStorage.setItem(STORAGE_KEY, normalized.url);
}

export async function clearUrlOverride(): Promise<void> {
  try {
    await AsyncStorage.removeItem(STORAGE_KEY);
  } catch {
    // Non-fatal if storage cannot be cleared.
  }
}
