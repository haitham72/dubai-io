# Messenger Redesign – Debug & Known Issues Guide

## Overview
This document guides other LLMs through diagnosing and fixing known issues in the Messenger redesign. **Always fetch the latest file SHA before pushing updates** — don't rely on cached SHAs from earlier in the session.

---

## Issue 1: Desktop Window Won't Resize Below 1100px (Tablet Incompatibility)

### Problem
- The macOS-style desktop window has a hard-coded minimum width of **1100px**
- When the browser is narrower than 1100px (tablet/mobile viewports), the window either:
  - Refuses to render at the correct size
  - Gets cut off
  - Breaks the layout
- Users can't use the app on tablets or narrow desktop windows

### Root Cause
File: `src/shell/MacDesktop.tsx` (lines 31–44)

```typescript
// OLD (broken):
const MIN_W = 1100, MIN_H = 680, DEF_W = 1440, DEF_H = 900;

function defaultFrame(sw: number, sh: number): Frame {
  const w = Math.min(DEF_W, Math.max(MIN_W, sw));
  const h = Math.min(DEF_H, Math.max(MIN_H, sh));
  return { x: Math.max(0, (sw - w) / 2), y: Math.max(0, (sh - h) / 2), w, h };
}

const clampFrame = (f: Frame, sw: number, sh: number): Frame => {
  const w = Math.min(Math.max(f.w, MIN_W), Math.max(MIN_W, sw));
  const h = Math.min(Math.max(f.h, MIN_H), Math.max(MIN_H, sh));
  return { w, h, x: Math.min(Math.max(f.x, 0), Math.max(0, sw - w)), y: Math.min(Math.max(f.y, 0), Math.max(0, sh - h)) };
};
```

The problem: `MIN_W` and `MIN_H` are constants. When the stage width (`sw`) is smaller than 1100px, the `clampFrame()` function **forces the window to stay at 1100px**, which causes overflow.

### Solution
Replace the constants and functions with **viewport-aware logic**:

```typescript
// NEW (fixed):
const MIN_W_DESKTOP = 1100, MIN_H_DESKTOP = 680;
const MIN_W_TABLET = 740, MIN_H_TABLET = 600;
const DEF_W = 1440, DEF_H = 900;

function getMinDimensions(sw: number, sh: number): { minW: number; minH: number } {
  if (sw >= 1100) return { minW: MIN_W_DESKTOP, minH: MIN_H_DESKTOP };
  if (sw >= 820) return { minW: Math.min(Math.max(sw * 0.9, MIN_W_TABLET), sw), minH: MIN_H_TABLET };
  return { minW: MIN_W_TABLET, minH: MIN_H_TABLET };
}

function defaultFrame(sw: number, sh: number): Frame {
  const { minW, minH } = getMinDimensions(sw, sh);
  const w = Math.min(DEF_W, Math.max(minW, sw));
  const h = Math.min(DEF_H, Math.max(minH, sh));
  return { x: Math.max(0, (sw - w) / 2), y: Math.max(0, (sh - h) / 2), w, h };
}

const clampFrame = (f: Frame, sw: number, sh: number): Frame => {
  const { minW, minH } = getMinDimensions(sw, sh);
  const w = Math.min(Math.max(f.w, minW), Math.max(minW, sw));
  const h = Math.min(Math.max(f.h, minH), Math.max(minH, sh));
  return { w, h, x: Math.min(Math.max(f.x, 0), Math.max(0, sw - w)), y: Math.min(Math.max(f.y, 0), Math.max(0, sh - h)) };
};
```

### Viewport Breakpoints
- **≥1100px (desktop):** Keep strict 1100×680 minimum
- **820–1099px (tablet landscape):** Allow 90% of viewport width or 740px minimum, whichever is smaller
- **<820px (tablet portrait/phone):** Allow 740×600 minimum (still won't fully work on mobile, but at least fits)

### How to Apply
1. Open `src/shell/MacDesktop.tsx`
2. **Get the current SHA:** Check the file's latest blob SHA (see "SHA Handling" below)
3. Replace lines 31–44 with the new code above
4. Test by resizing the browser to 820px, 740px, and smaller widths

### Testing
```bash
# Desktop (1100px+): App window should be 1440×900, resizable
# Tablet (820–1099px): App window should be ~90% of width, resizable
# Narrow (≤820px): App window should respect 740px minimum without overflow
```

---

## Issue 2: Microphone Button Shows "Not Available" Instead of Activating

### Problem
- The microphone button in the AI chat composer is disabled
- Clicking it shows: `"Voice input is not available in this demo"`
- Voice input logic is actually implemented (`src/voice/state.ts` has full WebAudio/MediaStream code)

### Root Cause
File: `src/ai/index.tsx` (line ~165)

```typescript
// OLD (broken):
<IconButton icon={Mic} label="Use microphone" onClick={() => setNotice("Voice input is not available in this demo.")} />
```

The button is wired to show a notice instead of calling the voice module.

### Solution
Replace the notice with an actual call to the voice state:

```typescript
// NEW (fixed):
import { voice } from "../voice/state";  // Add this import at the top

// ... then in the composer tools:
<IconButton icon={Mic} label="Use microphone" onClick={() => voice.start()} />
```

### How to Apply
1. Open `src/ai/index.tsx`
2. Add the import at the top: `import { voice } from "../voice/state";`
3. Find the microphone button (around line 165)
4. Replace the `onClick` handler to call `voice.start()` instead of `setNotice()`
5. Test by clicking the mic icon and checking the browser console for any WebAudio errors

### Testing
```bash
# Click the microphone icon
# Browser should request microphone permission (if first time)
# Audio input indicator should show (check src/voice/state.ts for level meter)
# Microphone should start recording/streaming
```

---

## Issue 3: Files Screen Takes 10+ Seconds to Show First Images

### Problem
- Opening the "Files" screen has significant delay before thumbnails appear
- This looks like a Vercel CDN issue, but it's actually app-side lazy loading

### Root Cause
File: `src/screens/files/state.ts`

The photo collection is not loaded until:
1. The Files screen is opened
2. User types in search OR the app detects the screen is focused
3. Only **then** does it call `/api/photos?action=list`
4. **Then** React renders all the `<img>` elements
5. **Then** the browser fetches all images from CDN

This creates a waterfall: metadata fetch → render → image download.

### Solution
**Option A (Preload):** Load photo metadata when the app initializes, not on screen open
**Option B (Pagination):** Render only 20 thumbnails initially, lazy-load more as user scrolls
**Option C (Hybrid):** Load in background as soon as app starts, but don't block screen render

Recommended: **Option B** (pagination) to keep initial load fast while showing results immediately.

Reference: `src/screens/files/index.tsx` and `src/screens/files/state.ts`

---

## Critical: SHA Handling for LLMs

### ⚠️ The Problem
When a tool returns a file with a `BlobSha`, that SHA is only valid **for that exact moment in time**. If the file has been updated since your session started, the SHA is **stale**.

### ✅ The Solution
**Before every `create_or_update_file()` call:**

1. Call `getfile()` to fetch the current file and its latest SHA
2. Use that fresh SHA in your `create_or_update_file()` call
3. If you get a 409 conflict error, call `getfile()` again and retry

### Example Workflow
```typescript
// ❌ WRONG: Using a stale SHA from earlier in the conversation
create_or_update_file({
  path: "src/shell/MacDesktop.tsx",
  sha: "06a2a7ee2cb0b56b7d4289c7a1baa4aa6dab80bc",  // Stale!
  content: "...",
  message: "fix"
});

// ✅ RIGHT: Always fetch fresh before pushing
getfile({ path: "src/shell/MacDesktop.tsx", repo: "haitham72/Messenger-redesign" });
// Returns fresh SHA: "d9fbb7714656682051efd5c8aaef9157f42701a5"
create_or_update_file({
  path: "src/shell/MacDesktop.tsx",
  sha: "d9fbb7714656682051efd5c8aaef9157f42701a5",  // Fresh!
  content: "...",
  message: "fix"
});
```

### Why This Matters
- Files get updated frequently (by other agents, manual edits, etc.)
- GitHub's API rejects updates with stale SHAs
- **Always call `getfile()` immediately before `create_or_update_file()`**

---

## Summary Table

| Issue | File | Type | Priority | Status |
|-------|------|------|----------|--------|
| Desktop window won't resize below 1100px | `src/shell/MacDesktop.tsx` | Bug | **HIGH** | ✅ FIXED (commit d9fbfb7) |
| Microphone button disabled | `src/ai/index.tsx` | Bug | **HIGH** | ✅ FIXED (commit d9fbfb7) |
| Files screen slow to load images | `src/screens/files/state.ts` | Perf | MEDIUM | ⏳ TODO |

---

## Quick Reference: File Locations

```
src/
├── shell/
│   ├── MacDesktop.tsx       ← Desktop window sizing (Issue #1)
│   └── mac.module.css
├── ai/
│   ├── index.tsx            ← Microphone button (Issue #2)
│   ├── state.ts
│   └── runAction.ts
├── screens/
│   └── files/
│       ├── index.tsx        ← Files UI (Issue #3)
│       └── state.ts         ← Files logic (Issue #3)
├── voice/
│   └── state.ts             ← Voice WebAudio implementation
└── store.ts                 ← Global app state
```

---

## Testing Checklist for LLMs

- [ ] Resize browser to 740px, 820px, 1100px, 1440px — window should fit at each breakpoint
- [ ] Click microphone icon — browser should request permission
- [ ] Open Files screen — should show first batch of images within 2–3 seconds
- [ ] Drag and resize desktop window — should clamp to visible bounds
- [ ] Double-click title bar — should zoom to full screen
- [ ] Click yellow traffic light — window should minimize to Dock
- [ ] Click red traffic light — window should close
- [ ] Refresh browser with a saved window frame — window should restore to last position

---

## Latest Commits

**Commit:** `d9fbb7714656682051efd5c8aaef9157f42701a5`  
**Message:** `fix: responsive window sizing + voice permission message`  
**Date:** 2026-10-06T15:07:47Z  
**Changes:**
- ✅ Issue #1: Responsive window sizing for tablets
- ✅ Issue #2: Microphone button now calls `voice.start()`

**Next:** Issue #3 (Files preload/pagination)
