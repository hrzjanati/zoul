/**
 * Small gettext-style i18n: the English source text is the key, `t()` looks it up in the
 * dictionary of the current locale and falls back to the key itself. No dependency, no
 * extraction step — a new string is just written in English and added to fa.ts.
 *
 * زول: دو زبان — فارسی (پیش‌فرض، راست‌به‌چپ) و English. انتخاب روی هر دستگاه جدا در
 * localStorage نگه داشته می‌شود و از Settings ← App language عوض می‌شود. چینیِ OpenMuse
 * حذف شد. راهنما: docs/features/i18n.md
 */
import { useSyncExternalStore } from "react";
import en from "./en";
import fa from "./fa";

export type Locale = "fa" | "en";
export type LocaleSetting = Locale;

export const LOCALES: Array<{ value: LocaleSetting; label: string }> = [
  { value: "fa", label: "فارسی" },
  { value: "en", label: "English" },
];

/** زبان پیش‌فرض، صرف‌نظر از زبان مرورگر. */
export const DEFAULT_LOCALE: Locale = "fa";

const STORAGE_KEY = "zoul_locale";
const DICTS: Record<Locale, Record<string, string>> = { fa, en };

function load(): LocaleSetting {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v === "fa" || v === "en") return v;
  } catch {
    // private mode / no storage: stay on the default
  }
  return DEFAULT_LOCALE;
}

let setting: LocaleSetting = load();
const listeners = new Set<() => void>();

export function getLocaleSetting(): LocaleSetting {
  return setting;
}

export function getLocale(): Locale {
  return setting;
}

/** Text direction of a locale: Persian is right-to-left. */
export function localeDir(locale: Locale = getLocale()): "rtl" | "ltr" {
  return locale === "fa" ? "rtl" : "ltr";
}

export function setLocaleSetting(next: LocaleSetting): void {
  setting = next;
  try {
    localStorage.setItem(STORAGE_KEY, next);
  } catch {
    // fine — the choice lasts for this page then
  }
  applyLang();
  listeners.forEach((fn) => fn());
}

/**
 * `<html lang>` and `<html dir>` follow the locale so fonts, hyphenation, screen readers and
 * the whole layout (start/end, scroll direction, form controls) agree with the text.
 */
export function applyLang(): void {
  if (typeof document === "undefined") return;
  document.documentElement.lang = getLocale();
  document.documentElement.dir = localeDir();
}

function subscribe(fn: () => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

/** Re-renders the component when the locale changes. */
export function useLocale(): Locale {
  return useSyncExternalStore(subscribe, getLocale, getLocale);
}

export function useLocaleSetting(): LocaleSetting {
  return useSyncExternalStore(subscribe, getLocaleSetting, getLocaleSetting);
}

export type Vars = Record<string, string | number>;

/** A number in the locale's own digits: ۳ in Persian, 3 in English. Strings pass as they are. */
function formatVar(v: string | number): string {
  return typeof v === "number" ? v.toLocaleString(intlLocale(), { useGrouping: false }) : v;
}

function interpolate(text: string, vars?: Vars): string {
  if (!vars) return text;
  return text.replace(/\{(\w+)\}/g, (m, k: string) => (k in vars ? formatVar(vars[k]) : m));
}

/**
 * Translate `key` (the English text) into the current locale. `{name}` placeholders are
 * filled from `vars`. Unknown keys come back as themselves, so English never breaks.
 */
export function t(key: string, vars?: Vars): string {
  const dict = DICTS[getLocale()];
  return interpolate(dict[key] ?? key, vars);
}

/**
 * The server labels background work in English ("Working on your goal: Run a 10k",
 * "Check-in: …", "Reminder: …", "Routine: …", "Tidied memory"). Translate the fixed part
 * and keep what the user wrote.
 */
export function localLabel(label: string): string {
  const rest = (prefix: string) => ({ title: label.slice(prefix.length) });
  if (label.startsWith("Working on your goal: ")) {
    return t("Working on your goal: {title}", rest("Working on your goal: "));
  }
  if (label.startsWith("Check-in: ")) return t("Check-in: {title}", rest("Check-in: "));
  if (label.startsWith("Reminder: ")) return t("Reminder: {title}", rest("Reminder: "));
  if (label.startsWith("Routine: ")) return t("Routine: {title}", rest("Routine: "));
  if (label.startsWith("New mail: ")) return t("New mail: {title}", rest("New mail: "));
  if (label.startsWith("Coming up: ")) return t("Coming up: {title}", rest("Coming up: "));
  if (label.startsWith("Webhook: ")) return t("Webhook: {title}", rest("Webhook: "));
  return label === "Tidied memory" ? t("Tidied memory") : label;
}

/** `t` bound to the live locale: the component re-renders when the language changes. */
export function useT(): typeof t {
  useLocale();
  return t;
}

/** Locale tag for Intl / toLocale*String, so dates and numbers follow the UI language. */
export function intlLocale(): string {
  // fa-IR: تاریخ شمسی و ارقام فارسی، خودِ Intl انجامش می‌دهد.
  return getLocale() === "fa" ? "fa-IR" : "en-US";
}

/** Names of translated keys, for tests and for spotting strings that lack a translation. */
export function dictionaryKeys(locale: Locale): string[] {
  return Object.keys(DICTS[locale]);
}
