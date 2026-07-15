export interface SelectedNiche {
  name: string;
  category: string;
}

/** Controlled, muted per-category palette (enterprise-calm, not neon). */
export const CATEGORY_COLORS: Record<string, { chip: string; dot: string }> = {
  Technology: { chip: "bg-emerald-50 text-emerald-700 ring-emerald-600/15", dot: "bg-emerald-500" },
  Business: { chip: "bg-sky-50 text-sky-700 ring-sky-600/15", dot: "bg-sky-500" },
  Education: { chip: "bg-violet-50 text-violet-700 ring-violet-600/15", dot: "bg-violet-500" },
  "Health & Fitness": { chip: "bg-rose-50 text-rose-700 ring-rose-600/15", dot: "bg-rose-500" },
  Lifestyle: { chip: "bg-amber-50 text-amber-700 ring-amber-600/15", dot: "bg-amber-500" },
  Entertainment: { chip: "bg-indigo-50 text-indigo-700 ring-indigo-600/15", dot: "bg-indigo-500" },
  Custom: { chip: "bg-slate-100 text-slate-600 ring-slate-400/20", dot: "bg-slate-400" },
};

export function categoryColor(category: string) {
  return CATEGORY_COLORS[category] ?? CATEGORY_COLORS.Custom;
}

export const MAX_NICHE_LENGTH = 60;

/** Parse manual input (newline OR comma separated) → cleaned, de-duplicated names. */
export function parseManualInput(input: string, existing: string[] = []): string[] {
  const seen = new Set(existing.map((n) => n.toLowerCase()));
  const out: string[] = [];
  for (const raw of input.split(/[\n,]+/)) {
    const name = raw.trim().replace(/\s+/g, " ").slice(0, MAX_NICHE_LENGTH);
    if (!name) continue;
    const key = name.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(name);
  }
  return out;
}
