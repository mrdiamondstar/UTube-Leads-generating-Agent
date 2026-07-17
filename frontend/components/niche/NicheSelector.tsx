"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { api, Niche } from "@/lib/api";
import { useToast } from "@/lib/toast";
import { useClickOutside } from "@/lib/useClickOutside";
import { cx } from "@/components/ui";
import { ChevronDownIcon, CopyIcon, PlusIcon, XIcon } from "@/components/icons";
import { NicheModal } from "@/components/niche/NicheModal";
import { SelectedNiche, categoryColor } from "@/components/niche/types";

const FAV_KEY = "cip_niche_favorites";
const RECENT_KEY = "cip_niche_recent";

function readList(key: string): string[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(key) || "[]");
  } catch {
    return [];
  }
}

export function NicheSelector({
  value,
  onChange,
}: {
  value: SelectedNiche[];
  onChange: (v: SelectedNiche[]) => void;
}) {
  const { toast } = useToast();
  const [open, setOpen] = useState(false);
  const [niches, setNiches] = useState<Niche[]>([]);
  const [loading, setLoading] = useState(true);
  const [favorites, setFavorites] = useState<string[]>([]);
  const [recent, setRecent] = useState<string[]>([]);
  // Niches discovered within the reuse window — excluded from "Select all".
  const [recentlyRun, setRecentlyRun] = useState<string[]>([]);
  const [exportOpen, setExportOpen] = useState(false);
  const [editing, setEditing] = useState<number | null>(null);
  const exportRef = useRef<HTMLDivElement>(null);
  useClickOutside(exportRef, () => setExportOpen(false), exportOpen);

  useEffect(() => {
    setFavorites(readList(FAV_KEY));
    setRecent(readList(RECENT_KEY));
    api
      .niches()
      .then(setNiches)
      .catch(() => setNiches([]))
      .finally(() => setLoading(false));
    api
      .recentNiches()
      .then(setRecentlyRun)
      .catch(() => setRecentlyRun([]));
  }, []);

  const toggleFavorite = (name: string) => {
    setFavorites((prev) => {
      const next = prev.includes(name) ? prev.filter((n) => n !== name) : [name, ...prev];
      localStorage.setItem(FAV_KEY, JSON.stringify(next));
      return next;
    });
  };

  // Wrap selection changes to record newly-added niches as "recently used".
  const setSelected = (list: SelectedNiche[]) => {
    const before = new Set(value.map((s) => s.name.toLowerCase()));
    const added = list.filter((s) => !before.has(s.name.toLowerCase())).map((s) => s.name);
    if (added.length) {
      setRecent((prev) => {
        const next = [...added, ...prev.filter((n) => !added.includes(n))].slice(0, 12);
        localStorage.setItem(RECENT_KEY, JSON.stringify(next));
        return next;
      });
    }
    onChange(list);
  };

  const names = useMemo(() => value.map((s) => s.name), [value]);
  const asLines = names.join("\n");
  const asComma = names.join(", ");

  const copy = async (text: string, format: string) => {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      const n = names.length;
      toast(`Copied ${n} niche${n === 1 ? "" : "s"} ${format}.`);
    } catch {
      toast("Copy failed — check clipboard permissions.");
    }
    setExportOpen(false);
  };

  const download = () => {
    const blob = new Blob([asLines], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "niches.txt";
    a.click();
    URL.revokeObjectURL(url);
    toast(`Exported ${names.length} niches to niches.txt.`);
    setExportOpen(false);
  };

  const remove = (name: string) =>
    onChange(value.filter((s) => s.name.toLowerCase() !== name.toLowerCase()));

  const commitEdit = (index: number, next: string) => {
    setEditing(null);
    const clean = next.trim().replace(/\s+/g, " ");
    if (!clean) return remove(value[index].name);
    const dupe = value.some(
      (s, i) => i !== index && s.name.toLowerCase() === clean.toLowerCase(),
    );
    if (dupe) return;
    const copyArr = [...value];
    copyArr[index] = { ...copyArr[index], name: clean };
    onChange(copyArr);
  };

  return (
    <div>
      {/* Trigger + panel header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-slate-900">
              Selected: {value.length} niche{value.length === 1 ? "" : "s"}
            </span>
          </div>
          <p className="mt-0.5 text-xs text-slate-400">
            Choose the niches to discover creators in
          </p>
        </div>
        <button
          onClick={() => setOpen(true)}
          className="focus-ring inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:border-slate-400 hover:bg-slate-50"
        >
          <PlusIcon className="h-4 w-4 text-slate-500" />
          Select niche
        </button>
      </div>

      {/* Selected chips */}
      {value.length > 0 ? (
        <>
          <div className="mt-4 flex flex-wrap gap-2">
            {value.map((n, i) => {
              const color = categoryColor(n.category);
              if (editing === i) {
                return (
                  <input
                    key={`edit-${i}`}
                    autoFocus
                    defaultValue={n.name}
                    onBlur={(e) => commitEdit(i, e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") commitEdit(i, (e.target as HTMLInputElement).value);
                      if (e.key === "Escape") setEditing(null);
                    }}
                    className="focus-ring rounded-full border border-emerald-400 px-3 py-1 text-xs text-slate-800 outline-none"
                  />
                );
              }
              return (
                <span
                  key={`${n.name}-${i}`}
                  onDoubleClick={() => setEditing(i)}
                  title="Double-click to edit"
                  className={cx(
                    "group inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset transition",
                    color.chip,
                  )}
                >
                  <span className={cx("h-1.5 w-1.5 rounded-full", color.dot)} />
                  {n.name}
                  <button
                    onClick={() => remove(n.name)}
                    aria-label={`Remove ${n.name}`}
                    className="focus-ring -mr-0.5 rounded-full p-0.5 opacity-50 transition hover:opacity-100"
                  >
                    <XIcon className="h-3 w-3" />
                  </button>
                </span>
              );
            })}
          </div>

          {/* Panel actions */}
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <button
              onClick={() => copy(asLines, "successfully")}
              className="focus-ring inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
            >
              <CopyIcon className="h-3.5 w-3.5" />
              Copy
            </button>

            <div ref={exportRef} className="relative">
              <button
                onClick={() => setExportOpen((v) => !v)}
                className="focus-ring inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
              >
                Export
                <ChevronDownIcon className="h-3.5 w-3.5" />
              </button>
              {exportOpen && (
                <div className="absolute left-0 top-9 z-30 w-52 rounded-lg border border-slate-200/70 bg-white p-1 shadow-card-lg">
                  <MenuItem onClick={() => copy(asLines, "(one per line)")}>
                    Copy · one per line
                  </MenuItem>
                  <MenuItem onClick={() => copy(asComma, "(comma-separated)")}>
                    Copy · comma-separated
                  </MenuItem>
                  <MenuItem onClick={download}>Download .txt</MenuItem>
                </div>
              )}
            </div>

            <button
              onClick={() => onChange([])}
              className="focus-ring ml-auto rounded-lg px-3 py-1.5 text-xs font-medium text-slate-400 hover:text-rose-600"
            >
              Clear all
            </button>
          </div>
        </>
      ) : (
        <div className="mt-4 rounded-lg border border-dashed border-slate-200 bg-slate-50/50 px-4 py-6 text-center">
          <p className="text-sm text-slate-500">No niches selected</p>
          <p className="mt-0.5 text-xs text-slate-400">
            Click “Select niche” to choose from curated niches or add your own.
          </p>
        </div>
      )}

      {open && (
        <NicheModal
          onClose={() => setOpen(false)}
          niches={niches}
          loading={loading}
          selected={value}
          setSelected={setSelected}
          favorites={favorites}
          toggleFavorite={toggleFavorite}
          recent={recent}
          recentlyRun={recentlyRun}
        />
      )}
    </div>
  );
}

function MenuItem({ children, onClick }: { children: React.ReactNode; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="focus-ring w-full rounded-md px-3 py-2 text-left text-xs font-medium text-slate-600 transition hover:bg-slate-50"
    >
      {children}
    </button>
  );
}
