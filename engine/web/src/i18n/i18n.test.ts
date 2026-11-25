import { afterEach, describe, expect, it } from "vitest";
import { DEFAULT_LOCALE, LOCALES, dictionaryKeys, getLocale, localeDir, setLocaleSetting, t } from "./index";
import fa from "./fa";

// The app's source, as text, so the dictionary can be checked against what is actually rendered.
const SOURCES = import.meta.glob<string>(["../**/*.ts", "../**/*.tsx", "!../**/*.test.ts", "!../i18n/**"], {
  query: "?raw",
  import: "default",
  eager: true,
});

afterEach(() => setLocaleSetting("en"));

describe("locales", () => {
  it("is bilingual, Persian first and by default", () => {
    expect(LOCALES.map((l) => l.value)).toEqual(["fa", "en"]);
    expect(DEFAULT_LOCALE).toBe("fa");
  });

  it("writes Persian right to left", () => {
    setLocaleSetting("fa");
    expect(localeDir()).toBe("rtl");
    setLocaleSetting("en");
    expect(localeDir()).toBe("ltr");
  });
});

describe("t", () => {
  it("returns the English key when there is no translation", () => {
    setLocaleSetting("en");
    expect(t("Nothing here")).toBe("Nothing here");
    expect(t("Hi, {name}", { name: "Sam" })).toBe("Hi, Sam");
  });

  it("uses the brand in English", () => {
    setLocaleSetting("en");
    expect(t("Connect to your OpenMuse")).toBe("Connect to your Zoul");
  });

  it("translates, keeps placeholders and writes numbers in Persian digits", () => {
    setLocaleSetting("fa");
    expect(getLocale()).toBe("fa");
    expect(t("Feed")).toBe("فید");
    expect(t("Hi, I'm {name}.", { name: "زول" })).toBe("سلام، من زول هستم.");
    expect(t("{n} frames", { n: 3 })).toBe("۳ فریم");
    expect(t("{n} frames", { n: "3" })).toBe("3 فریم");
  });

  it("leaves unknown placeholders alone rather than printing undefined", () => {
    setLocaleSetting("en");
    expect(t("Due in {n} days")).toBe("Due in {n} days");
  });
});

/** Every `t("...")` literal in the app source. */
function sourceKeys(): Set<string> {
  const keys = new Set<string>();
  const re = /\bt\(\s*"((?:[^"\\]|\\.)*)"/g;
  for (const src of Object.values(SOURCES)) {
    for (const m of src.matchAll(re)) keys.add(m[1].replace(/\\"/g, '"'));
  }
  return keys;
}

describe("fa dictionary", () => {
  it("sees the app source", () => {
    expect(Object.keys(SOURCES).length).toBeGreaterThan(10);
  });

  it("covers every literal string the app translates", () => {
    const missing = [...sourceKeys()].filter((k) => !(k in fa)).sort();
    expect(missing, `strings without a Persian translation (add them to fa.ts):\n${missing.join("\n")}`).toEqual([]);
  });

  it("keeps the same placeholders as the English text", () => {
    const vars = (s: string) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();
    const broken = dictionaryKeys("fa").filter((k) => JSON.stringify(vars(k)) !== JSON.stringify(vars(fa[k])));
    expect(broken, `placeholders differ:\n${broken.join("\n")}`).toEqual([]);
  });

  it("has no empty translations", () => {
    expect(dictionaryKeys("fa").filter((k) => !fa[k].trim())).toEqual([]);
  });
});

describe("localLabel", () => {
  it("translates the fixed part of a server label and keeps the user's words", async () => {
    const { localLabel } = await import("./index");
    setLocaleSetting("fa");
    expect(localLabel("Working on your goal: Run a 10k")).toBe("کار روی هدفت: Run a 10k");
    expect(localLabel("Reminder: call mum")).toBe("یادآوری: call mum");
    expect(localLabel("Tidied memory")).toBe("حافظه مرتب شد");
    expect(localLabel("Something else")).toBe("Something else");
    setLocaleSetting("en");
    expect(localLabel("Check-in: Japanese")).toBe("Check-in: Japanese");
  });
});
