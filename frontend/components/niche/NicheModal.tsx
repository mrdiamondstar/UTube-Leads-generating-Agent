"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Niche } from "@/lib/api";
import { cx } from "@/components/ui";
import { useToast } from "@/lib/toast";
import { useClickOutside } from "@/lib/useClickOutside";
import { CheckIcon, PlusIcon, SearchIcon, StarIcon, XIcon } from "@/components/icons";
import {
  MAX_NICHE_LENGTH,
  SelectedNiche,
  categoryColor,
  parseManualInput,
} from "@/components/niche/types";

interface Props {
  onClose: () => void;
  niches: Niche[];
  loading: boolean;
  selected: SelectedNiche[];
  setSelected: (list: SelectedNiche[]) => void;
  favorites: string[];
  toggleFavorite: (name: string) => void;
  recent: string[];
}

export function NicheModal({
  onClose,
  niches,
  loading,
  selected,
  setSelected,
  favorites,
  toggleFavorite,
  recent,
}: Props) {
  const [tab, setTab] = useState<"recommended" | "manual">("recommended");
  const [search, setSearch] = useState("");
  const [mounted, setMounted] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  useClickOutside(panelRef, onClose);

  // Portal to <body> so a transformed ancestor (animate-fade-up) can't trap
  // this fixed overlay inside its stacking context and paint it behind cards.
  useEffect(() => setMounted(true), []);

  const selectedNames = useMemo(
    () => new Set(selected.map((s) => s.name.toLowerCase())),
    [selected],
  );

  const isSelected = (name: string) => selectedNames.has(name.toLowerCase());

  const toggle = (n: SelectedNiche) => {
    if (isSelected(n.name)) {
      setSelected(selected.filter((s) => s.name.toLowerCase() !== n.name.toLowerCase()));
    } else {
      setSelected([...selected, n]);
    }
  };

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return q ? niches.filter((n) => n.name.toLowerCase().includes(q)) : niches;
  }, [niches, search]);

  const grouped = useMemo(() => {
    const map = new Map<string, Niche[]>();
    for (const n of filtered) {
      if (!map.has(n.category)) map.set(n.category, []);
      map.get(n.category)!.push(n);
    }
    return Array.from(map.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  }, [filtered]);

  const favoriteNiches = filtered.filter((n) => favorites.includes(n.name));
  const recentNiches = recent
    .map((name) => niches.find((n) => n.name === name))
    .filter((n): n is Niche => !!n && filtered.includes(n));

  const selectAllFiltered = () => {
    const merged = [...selected];
    const have = new Set(selected.map((s) => s.name.toLowerCase()));
    for (const n of filtered) {
      if (!have.has(n.name.toLowerCase())) merged.push({ name: n.name, category: n.category });
    }
    setSelected(merged);
  };

  if (!mounted) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Select niches"
    >
      <div
        ref={panelRef}
        className="flex h-[620px] max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl bg-white shadow-card-lg"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Select niches</h2>
            <p className="text-xs text-slate-400">
              Pick from curated niches or add your own
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="focus-ring flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          >
            <XIcon className="h-4 w-4" />
          </button>
        </div>

        {/* Tabs + Done */}
        <div className="flex items-center justify-between border-b border-slate-100 px-5">
          <div className="flex gap-1 pt-2">
            {(["recommended", "manual"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={cx(
                  "focus-ring relative px-3 py-2.5 text-sm font-medium capitalize transition",
                  tab === t ? "text-slate-900" : "text-slate-400 hover:text-slate-600",
                )}
              >
                {t === "manual" ? "Add manually" : "Recommended"}
                {tab === t && (
                  <span className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-emerald-500" />
                )}
              </button>
            ))}
          </div>
          <button
            onClick={onClose}
            aria-label="Done selecting niches"
            className="focus-ring inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-1.5 text-sm font-medium text-white shadow-sm transition hover:bg-emerald-700 active:scale-[0.98]"
          >
            <CheckIcon className="h-4 w-4" />
            Done
            {selected.length > 0 && (
              <span className="ml-0.5 rounded-full bg-white/25 px-1.5 text-xs font-semibold tabular-nums">
                {selected.length}
              </span>
            )}
          </button>
        </div>

        {tab === "recommended" ? (
          <RecommendedTab
            loading={loading}
            search={search}
            setSearch={setSearch}
            grouped={grouped}
            favoriteNiches={favoriteNiches}
            recentNiches={recentNiches}
            isSelected={isSelected}
            toggle={toggle}
            favorites={favorites}
            toggleFavorite={toggleFavorite}
            filteredCount={filtered.length}
            selectAllFiltered={selectAllFiltered}
            clear={() => setSelected([])}
          />
        ) : (
          <ManualTab selected={selected} setSelected={setSelected} />
        )}

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-slate-100 bg-white px-5 py-3">
          <span className="text-sm text-slate-500">
            <span className="font-semibold text-slate-900">{selected.length}</span> niche
            {selected.length === 1 ? "" : "s"} selected
          </span>
          {selected.length > 0 && (
            <button
              onClick={() => setSelected([])}
              className="focus-ring rounded-lg px-3 py-1.5 text-sm font-medium text-slate-400 hover:text-rose-600"
            >
              Clear all
            </button>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}

function NicheRow({
  niche,
  selected,
  onToggle,
  isFavorite,
  onFavorite,
}: {
  niche: Niche;
  selected: boolean;
  onToggle: () => void;
  isFavorite: boolean;
  onFavorite: () => void;
}) {
  const color = categoryColor(niche.category);
  return (
    <div
      className={cx(
        "group flex items-center gap-3 rounded-lg border px-3 py-2 transition",
        selected
          ? "border-emerald-300 bg-emerald-50/50"
          : "border-slate-200 bg-white hover:border-slate-300",
      )}
    >
      <button
        onClick={onToggle}
        role="checkbox"
        aria-checked={selected}
        aria-label={niche.name}
        className={cx(
          "focus-ring flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-md border transition",
          selected
            ? "border-emerald-600 bg-emerald-600 text-white"
            : "border-slate-300 bg-white text-transparent group-hover:border-slate-400",
        )}
      >
        <CheckIcon className="h-3.5 w-3.5" />
      </button>
      <button onClick={onToggle} className="flex min-w-0 flex-1 items-center gap-2 text-left">
        <span className={cx("h-1.5 w-1.5 flex-shrink-0 rounded-full", color.dot)} />
        <span className="truncate text-sm text-slate-700">{niche.name}</span>
      </button>
      <button
        onClick={onFavorite}
        aria-label={isFavorite ? "Unpin" : "Pin"}
        className={cx(
          "focus-ring flex-shrink-0 rounded p-1 transition",
          isFavorite ? "text-amber-500" : "text-slate-300 hover:text-slate-400",
        )}
      >
        <StarIcon className="h-4 w-4" filled={isFavorite} />
      </button>
    </div>
  );
}

function RecommendedTab(props: {
  loading: boolean;
  search: string;
  setSearch: (v: string) => void;
  grouped: [string, Niche[]][];
  favoriteNiches: Niche[];
  recentNiches: Niche[];
  isSelected: (name: string) => boolean;
  toggle: (n: SelectedNiche) => void;
  favorites: string[];
  toggleFavorite: (name: string) => void;
  filteredCount: number;
  selectAllFiltered: () => void;
  clear: () => void;
}) {
  const {
    loading,
    search,
    setSearch,
    grouped,
    favoriteNiches,
    recentNiches,
    isSelected,
    toggle,
    favorites,
    toggleFavorite,
    filteredCount,
    selectAllFiltered,
    clear,
  } = props;

  const row = (n: Niche) => (
    <NicheRow
      key={n.id}
      niche={n}
      selected={isSelected(n.name)}
      onToggle={() => toggle({ name: n.name, category: n.category })}
      isFavorite={favorites.includes(n.name)}
      onFavorite={() => toggleFavorite(n.name)}
    />
  );

  return (
    <>
      <div className="flex items-center gap-2 px-5 pb-3 pt-4">
        <div className="relative flex-1">
          <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            autoFocus
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search niches…"
            aria-label="Search niches"
            className="focus-ring w-full rounded-lg border border-slate-200 bg-slate-50/60 py-2 pl-9 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-emerald-500 focus:bg-white"
          />
        </div>
        <button
          onClick={selectAllFiltered}
          className="focus-ring whitespace-nowrap rounded-lg border border-slate-200 px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50"
        >
          Select all
        </button>
        <button
          onClick={clear}
          className="focus-ring whitespace-nowrap rounded-lg px-3 py-2 text-xs font-medium text-slate-400 hover:text-rose-600"
        >
          Clear
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-5 pb-4">
        {loading ? (
          <p className="py-10 text-center text-sm text-slate-400">Loading niches…</p>
        ) : filteredCount === 0 ? (
          <p className="py-10 text-center text-sm text-slate-400">
            No niches match “{search}”. Try the “Add manually” tab.
          </p>
        ) : (
          <div className="space-y-6">
            {favoriteNiches.length > 0 && (
              <Section title="Pinned">
                <Grid>{favoriteNiches.map(row)}</Grid>
              </Section>
            )}
            {recentNiches.length > 0 && (
              <Section title="Recently used">
                <Grid>{recentNiches.map(row)}</Grid>
              </Section>
            )}
            {grouped.map(([category, items]) => (
              <Section key={category} title={category} count={items.length}>
                <Grid>{items.map(row)}</Grid>
              </Section>
            ))}
          </div>
        )}
      </div>
    </>
  );
}

function Section({
  title,
  count,
  children,
}: {
  title: string;
  count?: number;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="mb-2 flex items-center gap-2">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">{title}</h3>
        {count !== undefined && <span className="text-xs text-slate-300">{count}</span>}
      </div>
      {children}
    </div>
  );
}

function Grid({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">{children}</div>;
}

function ManualTab({
  selected,
  setSelected,
}: {
  selected: SelectedNiche[];
  setSelected: (list: SelectedNiche[]) => void;
}) {
  const { toast } = useToast();
  const [text, setText] = useState("");
  const preview = parseManualInput(
    text,
    selected.map((s) => s.name),
  );

  const add = () => {
    if (preview.length === 0) return;
    setSelected([...selected, ...preview.map((name) => ({ name, category: "Custom" }))]);
    toast(`Added ${preview.length} niche${preview.length === 1 ? "" : "s"}.`);
    setText("");
  };

  const remove = (name: string) =>
    setSelected(selected.filter((s) => s.name.toLowerCase() !== name.toLowerCase()));

  const custom = selected.filter((s) => s.category === "Custom");

  return (
    <div className="flex-1 overflow-y-auto px-5 py-4">
      <label className="mb-1.5 block text-sm font-medium text-slate-700">Enter niches</label>
      <p className="mb-2 text-xs text-slate-400">
        One per line, or comma-separated. Spaces are cleaned and duplicates removed.
      </p>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
            e.preventDefault();
            add();
          }
        }}
        rows={5}
        placeholder={"AI Automation\nLinkedIn Growth\nYouTube Shorts, B2B SaaS"}
        className="focus-ring w-full resize-none rounded-lg border border-slate-200 bg-slate-50/60 p-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-emerald-500 focus:bg-white"
      />

      {preview.length > 0 && (
        <div className="mt-3">
          <p className="mb-2 text-xs font-medium text-slate-500">
            {preview.length} new tag{preview.length === 1 ? "" : "s"} preview
          </p>
          <div className="flex flex-wrap gap-1.5">
            {preview.map((name) => (
              <span
                key={name}
                className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600"
              >
                <span className="h-1.5 w-1.5 rounded-full bg-slate-400" />
                {name}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Prominent add button (right below input, always visible) */}
      <div className="mt-4 flex items-center gap-3">
        <button
          onClick={add}
          disabled={preview.length === 0}
          className="focus-ring inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <PlusIcon className="h-4 w-4" />
          Add {preview.length > 0 ? preview.length : ""} niche{preview.length === 1 ? "" : "s"}
        </button>
        <span className="text-xs text-slate-400">
          Press ⌘/Ctrl + Enter · max {MAX_NICHE_LENGTH} chars each
        </span>
      </div>

      {/* Already-added custom niches — visible so users see them accumulate */}
      {custom.length > 0 && (
        <div className="mt-6 border-t border-slate-100 pt-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
            Added manually · {custom.length}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {custom.map((n) => (
              <span
                key={n.name}
                className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600"
              >
                <span className="h-1.5 w-1.5 rounded-full bg-slate-400" />
                {n.name}
                <button
                  onClick={() => remove(n.name)}
                  aria-label={`Remove ${n.name}`}
                  className="focus-ring -mr-0.5 rounded-full p-0.5 text-slate-400 hover:text-rose-600"
                >
                  <XIcon className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
