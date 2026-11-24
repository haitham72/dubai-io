/** Light palette matching packages/design-tokens. Separation is a 1px hairline; no shadows. */
export const theme = {
  canvas: "#FFFFFF",
  surface: "#FAF8F5",
  ink: "#1E2022",
  muted: "#6B6560",
  border: "#E8E8EC",
  gold: "#C5A059",
  goldSurface: "#FDF8EE",
  goldBorder: "#E8D5A3",
  hairline: "rgba(0, 0, 0, 0.06)",
} as const;

export const flat = {
  boxShadow: "none",
  border: `1px solid ${theme.border}`,
} as const;
