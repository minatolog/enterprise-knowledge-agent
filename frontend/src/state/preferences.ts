import type { Connection, Mode } from "../api";

const KEY = "cnooc-assistant-preferences-v2";
const TOKEN_KEY = "cnooc-assistant-enterprise-token";

export interface Preferences {
  mode: Mode;
  topK: number;
  saveHistory: boolean;
  /** Token is kept only for this browser tab unless the person opts in. */
  rememberToken: boolean;
}

export const defaults: Preferences = { mode: "local", topK: 3, saveHistory: false, rememberToken: false };

export function loadPreferences(): Preferences {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) || "{}");
    return {
      mode: raw.mode === "enterprise" ? "enterprise" : "local",
      topK: Number.isInteger(raw.topK) && raw.topK >= 1 && raw.topK <= 10 ? raw.topK : defaults.topK,
      saveHistory: raw.saveHistory === true,
      rememberToken: raw.rememberToken === true,
    };
  } catch {
    return { ...defaults };
  }
}

export function savePreferences(value: Preferences) {
  try {
    localStorage.setItem(KEY, JSON.stringify(value));
  } catch {
    /* Preferences stay in memory. */
  }
}

export function loadToken(): string {
  try {
    return sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem(TOKEN_KEY) || "";
  } catch {
    return "";
  }
}

export function saveToken(token: string, remember: boolean) {
  try {
    sessionStorage.setItem(TOKEN_KEY, token);
    if (remember) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* Token stays in memory. */
  }
}

export function connectionOf(prefs: Preferences, token: string): Connection {
  return { mode: prefs.mode, token };
}
