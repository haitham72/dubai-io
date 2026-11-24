// Shared state for the Files screen: the sidebar (categories) and the main view
// are separate components, so selection + the real photo collection live here.
import { createStore } from "../../storeFactory";
import { listPhotos, type PhotoHit } from "../../api";

interface FilesState {
  category: string | null;
  photos: PhotoHit[];
  /** Size of the whole collection (known after the first page). */
  photosTotal: number;
  photosLoaded: boolean;
  photosLoading: boolean;
}
const filesStore = createStore<FilesState>({ category: null, photos: [], photosTotal: 0, photosLoaded: false, photosLoading: false });
const getFiles = filesStore.get;
const set = filesStore.set;


export function useFiles() { return filesStore.useState(); }

const FIRST_PAGE = 24;
const REST_PAGE = 200;

// Newest first by filename-parsed date ("20 May 2026"); undated rows sink.
const byDate = (a: PhotoHit, b: PhotoHit) => {
  const ta = Date.parse(a.meta.date ?? "");
  const tb = Date.parse(b.meta.date ?? "");
  if (Number.isNaN(ta) && Number.isNaN(tb)) return b.file.localeCompare(a.file);
  if (Number.isNaN(ta)) return 1;
  if (Number.isNaN(tb)) return -1;
  return tb - ta || b.file.localeCompare(a.file);
};

/** Merge a page into the list (deduped by file), keeping newest-first order. */
function merge(page: PhotoHit[]) {
  const seen = new Set(getFiles().photos.map((h) => h.file));
  return [...getFiles().photos, ...page.filter((h) => !seen.has(h.file))].sort(byDate);
}

/** First page right away (paints Quick Access + Photos), then the rest in the background. */
function loadPhotos() {
  if (getFiles().photosLoaded || getFiles().photosLoading) return;
  set({ photosLoading: true });
  (async () => {
    let r = await listPhotos(FIRST_PAGE, 0);
    set({ photos: merge(r.results), photosTotal: r.total });
    let offset = r.offset + r.count;
    while (r.count > 0 && offset < r.total) {
      r = await listPhotos(REST_PAGE, offset);
      set({ photos: merge(r.results), photosTotal: r.total });
      offset += r.count;
    }
    set({ photosLoaded: true });
  })()
    .catch(() => {})
    .finally(() => set({ photosLoading: false }));
}

export const files = {
  category: (category: string | null) => {
    set({ category });
    if (category === "images") loadPhotos();
  },
  /** The search bar fuzzy-filters this list as you type, so it loads on first focus. */
  loadPhotos,
};
