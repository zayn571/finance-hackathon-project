// Categorical palette. Both modes were validated with the dataviz skill's
// validate_palette.js (six checks: lightness band, chroma floor, CVD separation,
// normal-vision floor, contrast). Do not hand-edit these values — re-run the
// validator against the target surface if they need to change.
//
//   light  1B6CA8,00A5A2,C2185B  → all checks pass (contrast WARN on teal:
//          relieved by the direct value labels every chart carries)
//   dark   3284D0,1C985A,BC598C  → all checks pass (CVD WARN sits in the 6–8
//          floor band: relieved by direct labels + 2px segment gaps)
//
// The brand navy #0B2D4C fails as a categorical slot (L 0.291, chroma 0.069 —
// reads gray), so charts use the lighter brand blue below. Navy stays in use for
// text, headers and table bands, where it is ink rather than a data mark.
export const SERIES = {
  light: ["#1B6CA8", "#00A5A2", "#C2185B"],
  dark: ["#3284D0", "#1C985A", "#BC598C"],
};

export const AXIS = { light: "#6B7A8A", dark: "#9BA6B2" };
export const BASELINE = { light: "#E4E9EE", dark: "#33383D" };
export const SURFACE = { light: "#FFFFFF", dark: "#1A1A19" };

export type Mode = "light" | "dark";

export function useMode(): Mode {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}
