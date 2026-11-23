// Files workspace (R15). Owned by T07-stocks-files.
// Contract: export `filesScreen` = { Sidebar, Main } (see src/screens.ts).
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Cloud, Folder, FileText, Image as ImageIcon, MoreHorizontal,
  Paperclip, Search, Star, Trash2, UploadCloud, Video,
  Grid3X3, List, Clock, Share2, FileType2, Music, Film, X, Send, Sparkles,
} from "lucide-react";
import { Backdrop, Button, ICON, IconButton, SidebarHeader } from "../../ui";
import { actions, useStore } from "../../store";
import { searchPhotos, type PhotoHit } from "../../api";
import { files, useFiles } from "./state";
import { fuzzyPhotos } from "./fuzzy";
import {
  categories, typeCategories, cloudSources, recentFiles, sharedWithMe,
  fileTypeIconName, fileGroups, type FileItem, type SharedItem,
} from "./data";
import s from "./files.module.css";

/* Lucide icon lookup by type name string */
const IconMap: Record<string, typeof ImageIcon> = {
  Image: ImageIcon, Film: Video, FileText, FileType2, Music, Folder, Sparkles,
};

type NavKey = "all" | "recent" | "shared" | "starred" | "trash" | string;

/* ---- Sidebar ---- */
function FilesSidebar() {
  const [activeNav, setActiveNav] = useState<NavKey>("all");
  const { category, photosTotal } = useFiles();
  const genCount = useStore((st) => st.tasks.filter((t) =>
    t.status === "completed" && !t.dismissed && t.result !== undefined &&
    (t.result.type === "image" || t.result.type === "video")).length);
  const [uploadedNames, setUploadedNames] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleUpload = (names: string[]) => {
    setUploadedNames((prev) => [...names, ...prev].slice(0, 5));
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const files = Array.from(e.dataTransfer.files).map((f) => f.name);
    handleUpload(files);
  }, []);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []).map((f) => f.name);
    handleUpload(files);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }, []);

  return (
    <div className={s.sidebar}>
      <SidebarHeader title="Files">
        <IconButton icon={UploadCloud} label="Upload" />
        <IconButton icon={MoreHorizontal} label="More" />
      </SidebarHeader>
      {/* Upload zone */}
      <div className={s.uploadCard}>
        <div
          className={`${s.dropZone} ${dragOver ? s.dragOver : ""}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <div className={s.dropIcon}><UploadCloud size={18} strokeWidth={ICON.strokeWidth} /></div>
          <div className={s.dropText}>Drop files here or click to upload</div>
          <div className={s.dropSub}>Any file type supported</div>
        </div>
        <input ref={fileInputRef} type="file" multiple accept="*/*" className="sr-only" style={{ display: "none" }} onChange={handleFileInput} />
        {uploadedNames.length > 0 && (
          <div className={s.uploadedNames}>
            {uploadedNames.map((n, i) => (
              <div key={i} className={s.uploadedName}>✓ {n}</div>
            ))}
          </div>
        )}
      </div>

      {/* Nav */}
      <div className={s.navSection}>
        <div className={s.navLabel}>Locations</div>
        {categories.map((cat) => (
          <button key={cat.id} className={`${s.navItem} ${activeNav === cat.id ? s.navItemActive : ""}`}
            onClick={() => setActiveNav(cat.id)}>
            {cat.id === "all" && <Folder size={18} strokeWidth={ICON.strokeWidth} className={s.navIcon} />}
            {cat.id === "recent" && <Clock size={18} strokeWidth={ICON.strokeWidth} className={s.navIcon} />}
            {cat.id === "shared" && <Share2 size={18} strokeWidth={ICON.strokeWidth} className={s.navIcon} />}
            {cat.id === "starred" && <Star size={18} strokeWidth={ICON.strokeWidth} className={s.navIcon} />}
            {cat.id === "trash" && <Trash2 size={18} strokeWidth={ICON.strokeWidth} className={s.navIcon} />}
            <span className={s.navTitle}>{cat.label}</span>
            <span className={s.navCount}>{cat.count}</span>
          </button>
        ))}
      </div>

      {/* Categories */}
      <div className={s.catSection}>
        <div className={s.navLabel}>Categories</div>
        {typeCategories.map((cat) => {
          const Ico = IconMap[cat.icon] ?? FileText;
          return (
            <button
              key={cat.id}
              className={`${s.catItem} ${category === cat.id ? s.catItemActive : ""}`}
              aria-pressed={category === cat.id}
              onClick={() => files.category(category === cat.id ? null : cat.id)}
            >
              <div className={s.catIconWrap}><Ico size={18} strokeWidth={ICON.strokeWidth} /></div>
              <span className={s.catTitle}>{cat.label}</span>
              <span className={s.catCount}>{cat.id === "images" && photosTotal ? photosTotal : cat.id === "generated" ? genCount : cat.count}</span>
            </button>
          );
        })}
      </div>

      {/* Cloud storage */}
      <div className={s.cloudSection}>
        <div className={s.navLabel}>Cloud Storage</div>
        {cloudSources.map((src) => {
          const pct = Math.round((src.used / src.total) * 100);
          return (
            <div key={src.name} className={s.cloudItem}>
              <div className={s.cloudHeader}>
                <span className={s.cloudName}>{src.name}</span>
                <span className={s.cloudPct}>{pct}%</span>
              </div>
              <div className={s.usageBar}>
                <div className={s.usageFill} style={{ width: `${pct}%`, background: src.color }} />
              </div>
              <div className={s.usageText}>{src.used} GB of {src.total} GB used</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ---- File card (thumbnail or icon tile) ---- */
function FileCard({ file }: { file: FileItem }) {
  const isImage = file.type === "image" || file.type === "video";
  const Ico = IconMap[fileTypeIconName(file.type)] ?? FileText;
  const tileColor = file.type === "pdf" ? "var(--danger)" : file.type === "audio" ? "var(--purple)" : file.type === "folder" ? "var(--warning)" : "var(--blue)";
  return (
    <div className={s.fileCard}>
      <div className={s.fileThumb}>
        {isImage && file.thumbnail ? (
          <img src={file.thumbnail} alt={file.name} />
        ) : (
          <div className={s.fileThumbIcon} style={{ background: `color-mix(in srgb, ${tileColor} 10%, transparent)`, color: tileColor }}>
            <Ico size={24} strokeWidth={ICON.strokeWidth} />
          </div>
        )}
      </div>
      <div className={s.fileInfo}>
        <div className={s.fileName}>{file.name}</div>
        <div className={s.fileMeta}>
          <span>{file.size}</span>
          <span>·</span>
          <span>{file.modified}</span>
        </div>
      </div>
    </div>
  );
}

/* ---- Document tile ---- */
function DocTile({ file }: { file: FileItem }) {
  const Ico = IconMap[fileTypeIconName(file.type)] ?? FileText;
  const tileColor = file.type === "pdf" ? "var(--danger)" : file.type === "audio" ? "var(--purple)" : file.type === "folder" ? "var(--warning)" : "var(--blue)";
  return (
    <div className={s.docTile}>
      <div className={s.docIcon} style={{ background: `color-mix(in srgb, ${tileColor} 10%, transparent)`, color: tileColor }}>
        <Ico size={18} strokeWidth={ICON.strokeWidth} />
      </div>
      <div className={s.docInfo}>
        <div className={s.docName}>{file.name}</div>
        <div className={s.docMeta}>{file.size} · {file.modified}</div>
      </div>
      <Star size={14} strokeWidth={ICON.strokeWidth} className={s.starBtn} />
    </div>
  );
}

/* ---- Photo search (annotated collection: CDN images + Postgres metadata) ---- */
const titleCase = (s?: string) =>
  (s ?? "").split(" ").map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w)).join(" ");

/** Photo results grid (shared by instant matches and server search). */
function PhotoGrid({ photos, onOpen }: { photos: PhotoHit[]; onOpen: (h: PhotoHit) => void }) {
  return (
    <div className={s.photoGrid}>
      {photos.map((h) => (
        <button key={h.file} className={s.photoCard} onClick={() => onOpen(h)}>
          <div className={s.photoThumb}><img src={h.url} alt={h.caption} loading="lazy" /></div>
          <div className={s.photoInfo}>
            <div className={s.photoTitle}>{titleCase(h.meta.event)}</div>
            <div className={s.photoMeta}>{h.meta.date ?? ""}</div>
            <div className={s.photoFile}>{h.file}</div>
            {(h.why?.length ?? 0) > 0 && (
              <div className={s.photoWhy}>
                {(h.why ?? []).map((w) => (
                  <span key={w} className={s.whyChip}>{w === "keyword" ? "Keyword" : "Semantic"}</span>
                ))}
              </div>
            )}
          </div>
        </button>
      ))}
    </div>
  );
}

const PAGE = 24;

/** The Images view: 24 photos at a time; the next page loads as the end scrolls into view
 *  (or on "Show more"), so the grid never asks for the whole collection at once. */
function PagedPhotos({ photos, total, onOpen }: { photos: PhotoHit[]; total: number; onOpen: (h: PhotoHit) => void }) {
  const [shown, setShown] = useState(PAGE);
  const more = useRef<HTMLDivElement>(null);
  const hasMore = shown < photos.length;
  useEffect(() => {
    const el = more.current;
    if (!el || !hasMore) return;
    const io = new IntersectionObserver((e) => { if (e[0].isIntersecting) setShown((n) => n + PAGE); }, { rootMargin: "200px" });
    io.observe(el);
    return () => io.disconnect();
  }, [hasMore, shown]);
  return (
    <>
      <PhotoGrid photos={photos.slice(0, shown)} onOpen={onOpen} />
      {hasMore ? (
        <div ref={more} className={s.showMore}>
          <Button onClick={() => setShown((n) => n + PAGE)}>Show more · {Math.max(total, photos.length) - shown} left</Button>
        </div>
      ) : photos.length < total && (
        <div className={s.showMore}>Loading more photos…</div>
      )}
    </>
  );
}

/** "AI generated" folder tile: a 2×2 collage of the newest Mirsal generations. */
function GeneratedFolder({ items, onOpen }: { items: PhotoHit[]; onOpen: () => void }) {
  const cells = [0, 1, 2, 3].map((i) => items[i]);
  return (
    <button className={s.folderTile} onClick={onOpen}>
      <div className={s.folderCollage}>
        {items.length === 0 ? (
          <div className={s.folderEmpty}><Folder {...ICON} /></div>
        ) : cells.map((h, i) => !h ? <span key={i} className={s.folderCell} /> : /\.(mp4|webm|mov)(\?|$)/i.test(h.url)
          ? <video key={h.file} className={s.folderCell} src={h.url} muted playsInline preload="metadata" />
          : <img key={h.file} className={s.folderCell} src={h.url} alt="" loading="lazy" />)}
      </div>
      <div className={s.folderInfo}>
        <span className={s.folderBadge}><Sparkles size={14} strokeWidth={ICON.strokeWidth} /></span>
        <div>
          <div className={s.folderTitle}>AI generated</div>
          <div className={s.folderSub}>{items.length === 0 ? "Nothing yet" : `${items.length} ${items.length === 1 ? "item" : "items"}`}</div>
        </div>
      </div>
    </button>
  );
}

function PhotoViewer({ hit, onClose }: { hit: PhotoHit; onClose: () => void }) {
  return (
    <Backdrop backdrop={s.viewer} onClose={onClose}>
      <div className={s.viewerCard} role="dialog" aria-modal="true" aria-label={hit.caption} onClick={(e) => e.stopPropagation()}>
        <button className={s.viewerClose} onClick={onClose} aria-label="Close">
          <X size={18} strokeWidth={ICON.strokeWidth} />
        </button>
        <img src={hit.url} alt={hit.caption} className={s.viewerImg} />
        <div className={s.viewerBody}>
          <div className={s.viewerTitle}>{titleCase(hit.meta.event)}{hit.meta.date ? ` · ${hit.meta.date}` : ""}</div>
          <div className={s.viewerFile}>{hit.file}</div>
          {(hit.tags ?? []).length > 0 && (
            <div className={s.viewerTags}>{hit.tags.map((t) => <span key={t} className={s.viewerTag}>{t}</span>)}</div>
          )}
          <button
            className={s.viewerUse}
            onClick={() => { actions.sendToChat({ kind: "image", url: hit.url, caption: titleCase(hit.meta.event) }); onClose(); }}
          >
            <Send size={16} strokeWidth={ICON.strokeWidth} /> Use in chat
          </button>
        </div>
      </div>
    </Backdrop>
  );
}

/* ---- Main ---- */
function FilesMain() {
  const [activeView, setActiveView] = useState<"grid" | "list">("grid");
  const { category, photos, photosTotal, photosLoading } = useFiles();
  const [starredFiles, setStarredFiles] = useState<Set<string>>(new Set());

  // Mirsal-generated images/videos (completed, not dismissed) live under the Generated category.
  const tasks = useStore((st) => st.tasks);
  const generated: PhotoHit[] = [];
  for (const t of tasks) {
    if (t.status !== "completed" || t.dismissed || !t.result) continue;
    if (t.result.type !== "image" && t.result.type !== "video") continue;
    const url = t.result.type === "image" ? t.result.imageUrl : t.result.videoUrl;
    generated.push({ file: t.id, meta: { account: "mirsal", event: t.title }, caption: "", tags: [], url });
  }

  // Photo search. Typing (2+ chars) fuzzy-filters the loaded photos instantly;
  // Enter asks the server (keyword + semantic). `searched` = the submitted query.
  const [query, setQuery] = useState("");
  const [searched, setSearched] = useState<string | null>(null);
  const [hits, setHits] = useState<PhotoHit[]>([]);
  const [searching, setSearching] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [viewer, setViewer] = useState<PhotoHit | null>(null);
  const live = useMemo(() => fuzzyPhotos(photos, query), [photos, query]);
  useEffect(() => files.loadPhotos(), []); // real photos show in All Files straight away
  const liveActive = searched === null && query.trim().length >= 2;

  const runSearch = useCallback(async (text: string) => {
    const t = text.trim();
    if (!t) { setSearched(null); setHits([]); return; }
    setSearching(true); setSearched(t);
    const start = performance.now();
    try {
      const r = await searchPhotos(t);
      setHits(r.results);
      setElapsed((performance.now() - start) / 1000);
    } catch {
      setHits([]);
    } finally {
      setSearching(false);
    }
  }, []);

  const onQueryChange = (v: string) => {
    setQuery(v);
    if (v.trim().length >= 2) files.loadPhotos();
    // Editing after Enter drops back to instant matching.
    if (searched !== null) { setSearched(null); setHits([]); }
  };
  const clearSearch = () => { setQuery(""); setSearched(null); setHits([]); };

  const toggleStar = (id: string) => {
    setStarredFiles((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  // Filter files based on active category (sidebar + dropdown share one selection).
  // Type filter ids are plural ("images"); FileItem.type is singular ("image").
  const typeOf: Record<string, FileItem["type"]> = { images: "image", videos: "video", documents: "document", pdfs: "pdf", audio: "audio", folders: "folder" };
  const filteredFiles = category && category !== "images"
    ? recentFiles.filter((f) => f.type === typeOf[category])
    : recentFiles;
  const grouped = fileGroups.map((g) => [g, filteredFiles.filter((f) => f.group === g)] as const).filter(([, list]) => list.length);

  return (
    <div className={s.main}>
      <div className={s.mainInner}>
        {/* Top bar */}
        <div className={s.topBar}>
          <h2 className={s.topBarTitle}>Files</h2>
          <div className={s.topBarActions}>
            <IconButton icon={Cloud} label="Cloud" />
            <IconButton icon={MoreHorizontal} label="More" />
          </div>
        </div>

        {/* Ask bar + view toggle */}
        <div className={s.askBar}>
          <label className={s.askField}>
            <Sparkles {...ICON} />
            <input
              className={s.askInput}
              placeholder="Search or ask about your files…"
              value={query}
              onFocus={() => files.loadPhotos()}
              onChange={(e) => onQueryChange(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") runSearch(query);
                if (e.key === "Escape") clearSearch();
              }}
            />
            {query && (
              <button className={s.clearBtn} onClick={clearSearch} aria-label="Clear search">
                <X size={14} strokeWidth={ICON.strokeWidth} /> Clear
              </button>
            )}
          </label>
          <div className={s.viewToggle}>
            <button className={`${s.viewBtn} ${activeView === "grid" ? s.viewBtnActive : ""}`}
              onClick={() => setActiveView("grid")} aria-label="Grid view">
              <Grid3X3 size={14} strokeWidth={ICON.strokeWidth} />
            </button>
            <button className={`${s.viewBtn} ${activeView === "list" ? s.viewBtnActive : ""}`}
              onClick={() => setActiveView("list")} aria-label="List view">
              <List size={14} strokeWidth={ICON.strokeWidth} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className={s.contentArea}>
          {searched !== null ? (
            <div className={s.section}>
              <div className={s.sectionHeader}>
                <div className={s.sectionTitle}>
                  {searching ? `Searching for “${searched}”…` : hits.length > 0 ? `Photos matching “${searched}”` : `No photos for “${searched}”`}
                </div>
                {!searching && hits.length > 0 && (
                  <span className={s.sectionLink}>Searched photos · {elapsed.toFixed(1)}s</span>
                )}
              </div>
              {searching && hits.length === 0 ? (
                <div className={s.emptyState}>
                  <div className={s.emptyIcon}><Search size={20} strokeWidth={ICON.strokeWidth} /></div>
                  <div>Searching the photo collection…</div>
                </div>
              ) : hits.length === 0 ? (
                <div className={s.emptyState}>
                  <div className={s.emptyIcon}><Search size={20} strokeWidth={ICON.strokeWidth} /></div>
                  <div>Nothing in the photo collection matches. Try “zayed”, “eid” or “يوم عرفة”.</div>
                </div>
              ) : (
                <PhotoGrid photos={hits} onOpen={setViewer} />
              )}
            </div>
          ) : liveActive ? (
            <div className={s.section}>
              <div className={s.sectionHeader}>
                <div className={s.sectionTitle}>
                  {live.length > 0 ? `${live.length} ${live.length === 1 ? "photo" : "photos"} matching “${query.trim()}”` : `No quick matches for “${query.trim()}”`}
                </div>
                <span className={s.sectionLink} onClick={() => runSearch(query)}>Press Enter to search by meaning</span>
              </div>
              {live.length === 0 ? (
                <div className={s.emptyState}>
                  <div className={s.emptyIcon}><Search size={20} strokeWidth={ICON.strokeWidth} /></div>
                  <div>{photos.length === 0 ? "Loading the photo collection…" : "Nothing matches by name. Press Enter and Mirsal will search by meaning."}</div>
                </div>
              ) : (
                <PhotoGrid photos={live.slice(0, 48)} onOpen={setViewer} />
              )}
            </div>
          ) : (
          <>
          {/* Quick Access (All Files + Images): the AI generated folder, then the newest real photos */}
          {(category === null || category === "images") && (
          <div className={s.section}>
            <div className={s.sectionHeader}>
              <div className={s.sectionTitle}>Quick Access</div>
            </div>
            <div className={s.quickGrid}>
              <GeneratedFolder items={generated} onOpen={() => files.category("generated")} />
              {photos.slice(0, 3).map((h) => (
                <button key={h.file} className={s.quickCard} onClick={() => setViewer(h)}>
                  <img src={h.url} alt={titleCase(h.meta.event)} />
                  <div className={s.quickCardShade}>
                    <div className={s.quickCardTitle}>{titleCase(h.meta.event)}</div>
                    <div className={s.quickCardSub}>{h.meta.date ?? ""}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>
          )}

          {/* All Files: the real photo collection comes first */}
          {category === null && photos.length > 3 && (
            <div className={s.section}>
              <div className={s.sectionHeader}>
                <div className={s.sectionTitle}>Photos</div>
                <span className={s.sectionLink} onClick={() => files.category("images")}>See all {photosTotal || photos.length}</span>
              </div>
              <PhotoGrid photos={photos.slice(3, 11)} onOpen={setViewer} />
            </div>
          )}

          {/* Recent Files */}
          <div className={s.section}>
            <div className={s.sectionHeader}>
              <div className={s.sectionTitle}>{category === "images" ? "Images" : category === "generated" ? "Generated" : "Recent Files"}</div>
              <div style={{ display: "flex", gap: "var(--s-2)", alignItems: "center" }}>
                <select
                  style={{ fontSize: "var(--fs-sm)", padding: "4px 8px", borderRadius: 8, border: "1px solid var(--border-strong)", background: "var(--surface-solid)", color: "var(--text)" }}
                  value={category ?? ""}
                  onChange={(e) => files.category(e.target.value || null)}
                >
                  <option value="">All types</option>
                  {typeCategories.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
                </select>
                <span className={s.sectionLink}>{category === "images" ? `${photosTotal || photos.length} photos` : category === "generated" ? `${generated.length} items` : `${filteredFiles.length} files`}</span>
              </div>
            </div>
            {category === "images" ? (
              photosLoading && photos.length === 0 ? (
                <div className={s.emptyState}>
                  <div className={s.emptyIcon}><Search size={20} strokeWidth={ICON.strokeWidth} /></div>
                  <div>Loading the photo collection…</div>
                </div>
              ) : photos.length === 0 ? (
                <div className={s.emptyState}>
                  <div className={s.emptyIcon}><Search size={20} strokeWidth={ICON.strokeWidth} /></div>
                  <div>No annotated photos yet.</div>
                </div>
              ) : (
                <PagedPhotos photos={photos} total={photosTotal} onOpen={setViewer} />
              )
            ) : category === "generated" ? (
              generated.length === 0 ? (
                <div className={s.emptyState}>
                  <div className={s.emptyIcon}><Sparkles size={20} strokeWidth={ICON.strokeWidth} /></div>
                  <div>No generated images yet — ask Mirsal to create one.</div>
                </div>
              ) : (
                <div className={s.photoGrid}>
                  {generated.map((h) => (
                    <button key={h.file} className={s.photoCard} onClick={() => setViewer(h)}>
                      <div className={s.photoThumb}><img src={h.url} alt={titleCase(h.meta.event)} loading="lazy" /></div>
                      <div className={s.photoInfo}>
                        <div className={s.photoTitle}>{titleCase(h.meta.event)}</div>
                        <div className={s.photoMeta}>Mirsal generated</div>
                      </div>
                    </button>
                  ))}
                </div>
              )
            ) : filteredFiles.length === 0 ? (
              <div className={s.emptyState}>
                <div className={s.emptyIcon}><Search size={20} strokeWidth={ICON.strokeWidth} /></div>
                <div>No files found for this filter.</div>
              </div>
            ) : activeView === "grid" ? (
              grouped.map(([group, list]) => <div key={group} className={s.fileGroup}>
              <div className={s.groupLabel}>{group}<span>{list.length}</span></div>
              <div className={s.fileGrid}>
                {list.map((file) => (
                  <div key={file.id} style={{ position: "relative" }}>
                    <FileCard file={file} />
                    <button className={`${s.starBtn} ${starredFiles.has(file.id) ? s.starred : ""}`}
                      style={{ position: "absolute", top: 8, right: 8 }}
                      onClick={() => toggleStar(file.id)}
                      aria-label={starredFiles.has(file.id) ? "Unstar" : "Star"}
                    >
                      <Star size={14} strokeWidth={ICON.strokeWidth} fill={starredFiles.has(file.id) ? "currentColor" : "none"} />
                    </button>
                  </div>
                ))}
              </div>
              </div>)
            ) : (
              grouped.map(([group, list]) => <div key={group} className={s.fileGroup}>
                <div className={s.groupLabel}>{group}<span>{list.length}</span></div>
                <div style={{ display: "flex", flexDirection: "column", gap: "var(--s-1)" }}>
                  {list.map((file) => <DocTile key={file.id} file={file} />)}
                </div>
              </div>)
            )}
          </div>

          {/* Shared with me */}
          <div className={s.section}>
            <div className={s.sectionHeader}>
              <div className={s.sectionTitle}>Shared with Me</div>
              <span className={s.sectionLink}>See all</span>
            </div>
            {sharedWithMe.length === 0 ? (
              <div className={s.emptyState}>
                <div className={s.emptyIcon}><Share2 size={20} strokeWidth={ICON.strokeWidth} /></div>
                <div>No shared files yet.</div>
              </div>
            ) : (
              <table className={s.sharedTable}>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Shared by</th>
                    <th>Permission</th>
                    <th>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {sharedWithMe.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <div className={s.sharedFile}>
                          {item.file.thumbnail ? (
                            <div className={s.sharedThumb}><img src={item.file.thumbnail} alt="" /></div>
                          ) : (
                            <div className={s.sharedThumb} style={{ display: "grid", placeItems: "center" }}>
                              {(() => {
                                const Ico = IconMap[fileTypeIconName(item.file.type)] ?? FileText;
                                const tileColor = item.file.type === "pdf" ? "var(--danger)" : item.file.type === "audio" ? "var(--purple)" : item.file.type === "folder" ? "var(--warning)" : "var(--blue)";
                                return <Ico size={18} strokeWidth={ICON.strokeWidth} color={tileColor} />;
                              })()}
                            </div>
                          )}
                          <div>
                            <div className={s.sharedFileName}>{item.file.name}</div>
                            <div className={s.sharedFileSize}>{item.file.size}</div>
                          </div>
                        </div>
                      </td>
                      <td>
                        <div className={s.sharerCell}>
                          <img src={item.sharerAvatar} alt={item.sharer} style={{ width: 28, height: 28, borderRadius: "50%", objectFit: "cover" }} />
                          <span style={{ fontSize: "var(--fs-sm)" }}>{item.sharer}</span>
                        </div>
                      </td>
                      <td>
                        <span className={`${s.permissionBadge} ${item.permission === "edit" ? s.permEdit : s.permView}`}>
                          {item.permission === "edit" ? "Can edit" : "Can view"}
                        </span>
                      </td>
                      <td style={{ fontSize: "var(--fs-sm)", color: "var(--text-3)" }}>{item.sharedAt}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          </>
          )}
        </div>
      </div>
      {viewer && <PhotoViewer hit={viewer} onClose={() => setViewer(null)} />}
    </div>
  );
}


export const filesScreen = { Sidebar: FilesSidebar, Main: FilesMain };
