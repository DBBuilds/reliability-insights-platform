// Light, dark, or the system setting. A per-browser preference, so it lives in storage, not the URL.
export const THEMES = ["system", "light", "dark"] as const;
export type Theme = (typeof THEMES)[number];

const KEY = "theme";

/** The stored choice, or "system" when there is none or storage is blocked (private windows can throw). */
export function storedTheme(): Theme {
  try {
    const value = localStorage.getItem(KEY);
    return THEMES.find((t) => t === value) ?? "system";
  } catch {
    return "system";
  }
}

/** Applies the choice to the page (styles.css reads `data-theme`) and remembers it when storage allows. */
export function setTheme(theme: Theme) {
  if (theme === "system") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.dataset.theme = theme;
  try {
    if (theme === "system") localStorage.removeItem(KEY);
    else localStorage.setItem(KEY, theme);
  } catch {
    // Without storage the choice lasts until the page closes.
  }
}
