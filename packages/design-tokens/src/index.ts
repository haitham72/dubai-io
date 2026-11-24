/**
 * Light canvas first. The 20 Nov catalog listed a soft card shadow;
 * the 23 Nov Expo plan locks separation to 1px hairlines (`shadow: 'none'`).
 * `palette.json` is the JSON twin (root gitignore blocks any `*token*.json`).
 */

export const mode = "light" as const;
export const shadow = "none" as const;

export const colors = {
  canvas: "#FFFFFF",
  surface: "#FAF8F5",
  card: "#FFFFFF",
  ink: "#1E2022",
  userBubble: "#1E2022",
  onUserBubble: "#FFFFFF",
  muted: "#6B6560",
  border: "#E8E8EC",
  borderHairline: "rgba(0, 0, 0, 0.06)",
  actionBox: "#FFFFFF",
  repairSurface: "#FDF8EE",
  ingested: "#27AE60",
  gold: {
    primary: "#C5A059",
    metallic: "#D4AF37",
    surface: "#FDF8EE",
    border: "#E8D5A3",
  },
  themes: {
    career: "#2F80ED",
    projects: "#9B51E0",
    learning: "#F2994A",
    gaming: "#EB5757",
    travel: "#00B4D8",
    health: "#27AE60",
  },
} as const;

export const gold = colors.gold;
export const themes = colors.themes;

export const radii = {
  card: 20,
  dock: 28,
  pill: 999,
  chip: 10,
  orb: 28,
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
} as const;

export const typography = {
  serif: "Georgia",
  sans: "System",
  display: 32,
  title: 22,
  body: 16,
  caption: 13,
  brand: 22,
} as const;

/** 3:4 portrait cards. */
export const cardAspectRatio = 3 / 4;
export const cardViewportWidth = 0.78;
export const cardPeekWidth = 0.18;

export const noShadow = {
  shadowColor: "transparent",
  shadowOpacity: 0,
  shadowRadius: 0,
  shadowOffset: { width: 0, height: 0 },
  elevation: 0,
} as const;

export const tokens = {
  mode,
  shadow,
  colors,
  gold,
  themes,
  radii,
  spacing,
  typography,
  cardAspectRatio,
  cardViewportWidth,
  cardPeekWidth,
  noShadow,
};

export type DesignTokens = typeof tokens;
