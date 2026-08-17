"use client";

import { createContext, useContext, useRef, useState, ReactNode } from "react";
import { api, setLastDiscovery } from "@/lib/api";
import { SelectedNiche } from "@/components/niche/types";

/** How deeply each niche is mined per run. */
export interface ScanMode {
  id: string;
  label: string;
  perNiche: number;
  nichesPerDay: number;
  note: string;
}

// Every mode above 20 yields roughly the same number of leads per day — the
// daily quota decides that, and it stops improving once a run fills a full
// search page. What the modes really trade is breadth against depth: how many
// niches get covered each day, versus how far into each one the tool digs.
export const SCAN_MODES: ScanMode[] = [
  { id: "quick",    label: "Quick",    perNiche: 20,  nichesPerDay: 81, note: "Most topics, shallowest" },
  { id: "wide",     label: "Wide",     perNiche: 50,  nichesPerDay: 64, note: "Broad coverage" },
  { id: "balanced", label: "Balanced", perNiche: 100, nichesPerDay: 32, note: "Recommended" },
  { id: "deep",     label: "Deep",     perNiche: 200, nichesPerDay: 16, note: "Fewest topics, digs furthest" },
];

const MODE_KEY = "cip_scan_mode";
const DEFAULT_MODE = SCAN_MODES[2]; // Balanced

interface DiscoveryContext {
  busy: boolean;
  progress: string | null;
  error: string | null;
  reusedNiches: string[];
  lastRunAt: number; // bumped each time a run finishes; pages watch it to refresh
  runDiscovery: (niches: SelectedNiche[], force?: boolean) => Promise<void>;
  clearReused: () => void;
  mode: ScanMode;
  setMode: (m: ScanMode) => void;
  // Auto mode: keep discovering the next not-recently-run niches, 8 at a time,
  // until every niche is covered (or the daily quota is reached).
  auto: boolean;
  autoProgress: string | null;
  runAuto: () => Promise<void>;
  stopAuto: () => void;
}

const Ctx = createContext<DiscoveryContext | null>(null);

const BATCH_SIZE = 8;
const CONCURRENCY = 3;

/**
 * Runs discovery ABOVE the page tree so it keeps going when the user navigates
 * to Leads or anywhere else — the loop lives here, not in a page component, so
 * client-side navigation never interrupts it. A floating pill shows progress on
 * every page while a run is in flight.
 */
export function DiscoveryProvider({ children }: { children: ReactNode }) {
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reusedNiches, setReusedNiches] = useState<string[]>([]);
  const [lastRunAt, setLastRunAt] = useState(0);
  const [auto, setAuto] = useState(false);
  const [autoProgress, setAutoProgress] = useState<string | null>(null);
  // Read on first render rather than in an effect, so the first run cannot fire
  // with the default depth before the saved choice has been applied.
  const [mode, setModeState] = useState<ScanMode>(() => {
    if (typeof window === "undefined") return DEFAULT_MODE;
    const saved = window.localStorage.getItem(MODE_KEY);
    return SCAN_MODES.find((m) => m.id === saved) ?? DEFAULT_MODE;
  });
  // A ref alongside the state: the discovery loop reads this between batches and
  // would otherwise close over whatever mode was set when the run started.
  const modeRef = useRef(mode);
  const setMode = (m: ScanMode) => {
    modeRef.current = m;
    setModeState(m);
    if (typeof window !== "undefined") window.localStorage.setItem(MODE_KEY, m.id);
  };
  const runningRef = useRef(false);
  const autoRef = useRef(false);
  const autoStopRef = useRef(false);

  /**
   * Core batch runner: discover `targets` with bounded parallelism (at most
   * CONCURRENCY at once) — ~3x faster than one-by-one while staying under
   * YouTube's per-second rate limits and not overloading the free backend.
   * A single niche failing does not abort the batch; the first error is
   * returned. `onProgress(done, total)` fires as each niche completes.
   */
  const processBatch = async (
    targets: SelectedNiche[],
    force: boolean,
    onProgress: (done: number, total: number) => void,
  ): Promise<{ runIds: string[]; reused: string[]; firstError: string | null }> => {
    const runIds: string[] = [];
    const reused: string[] = [];
    let firstError: string | null = null;
    let completed = 0;
    let cursor = 0;
    onProgress(0, targets.length);

    const worker = async () => {
      while (true) {
        const i = cursor++;
        if (i >= targets.length) return;
        try {
          const run = await api.runPipeline(targets[i].name, modeRef.current.perNiche, force);
          if (run?.id) runIds.push(run.id);
          if (run?.reused) reused.push(targets[i].name);
          // The endpoint records a failure on the run and still answers 201, so
          // without this a broken key or spent quota reads as "found nothing".
          if (run?.status === "failed" && !firstError) {
            firstError = run.error
              ? `${targets[i].name}: ${run.error}`
              : `${targets[i].name}: discovery failed`;
          }
        } catch (e) {
          if (!firstError) firstError = (e as Error).message;
        } finally {
          completed++;
          onProgress(completed, targets.length);
        }
      }
    };

    await Promise.all(
      Array.from({ length: Math.min(CONCURRENCY, targets.length) }, worker),
    );
    return { runIds, reused, firstError };
  };

  const runDiscovery = async (niches: SelectedNiche[], force = false) => {
    if (niches.length === 0 || runningRef.current || autoRef.current) return;
    runningRef.current = true;
    setBusy(true);
    setError(null);
    setReusedNiches([]);
    const targets = niches.slice(0, BATCH_SIZE);
    try {
      const { runIds, reused, firstError } = await processBatch(
        targets,
        force,
        (done, total) => setProgress(`Discovering ${done}/${total}…`),
      );
      setLastDiscovery(
        runIds,
        targets.map((t) => t.name),
      );
      setReusedNiches(reused);
      if (firstError) setError(firstError);
      setLastRunAt(Date.now());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
      setProgress(null);
      runningRef.current = false;
    }
  };

  const stopAuto = () => {
    autoStopRef.current = true;
  };

  const runAuto = async () => {
    if (runningRef.current || autoRef.current) return;
    autoRef.current = true;
    autoStopRef.current = false;
    setAuto(true);
    setError(null);
    setReusedNiches([]);

    const allRunIds: string[] = [];
    const doneNames: string[] = [];
    try {
      const all = await api.niches();
      // Drop niches that have run before and never yielded a lead. Priority is
      // a fixed catalog score, so without this a barren niche would be re-run
      // every day forever, spending a full search each time.
      const barren = new Set(
        (await api.unproductiveNiches().catch(() => [])).map((s) => s.toLowerCase()),
      );
      // Process in global priority order (popularity desc) so the daily quota
      // is spent on the highest-value lead niches first.
      const allTargets: SelectedNiche[] = [...all]
        .filter((n) => !barren.has(n.name.toLowerCase()))
        .sort((a, b) => (b.popularity ?? 0) - (a.popularity ?? 0))
        .map((n) => ({ name: n.name, category: n.category }));

      const recentSet = async () =>
        new Set((await api.recentNiches()).map((s) => s.toLowerCase()));
      let recent = await recentSet();
      let remaining = allTargets.filter((n) => !recent.has(n.name.toLowerCase()));
      const plannedTotal = remaining.length;
      let processed = 0;

      if (plannedTotal === 0) {
        setError(
          "All niches were already discovered in the last 24h — nothing new to auto-run right now.",
        );
      }

      // Hard cap on iterations as a final safety net against any infinite loop.
      let guard = 0;
      while (!autoStopRef.current && remaining.length > 0 && guard < 100) {
        guard++;
        const batch = remaining.slice(0, BATCH_SIZE);
        const before = remaining.length;

        const { runIds } = await processBatch(batch, false, (done, total) =>
          setAutoProgress(
            `Auto-discovering ${Math.min(processed + done, plannedTotal)}/${plannedTotal} niches · batch ${done}/${total}`,
          ),
        );
        allRunIds.push(...runIds);
        doneNames.push(...batch.map((b) => b.name));
        // Let pages refresh their data and "View leads" work mid-run.
        setLastDiscovery(allRunIds, doneNames);
        setLastRunAt(Date.now());

        if (autoStopRef.current) break;

        // Refresh the recently-run set and recompute what's left.
        recent = await recentSet();
        const nextRemaining = allTargets.filter(
          (n) => !recent.has(n.name.toLowerCase()),
        );
        // No-progress safeguard: if a whole batch completed but nothing new got
        // recorded as done, we've almost certainly hit the daily YouTube quota
        // (or every remaining niche is failing). Stop cleanly instead of looping.
        if (nextRemaining.length >= before) {
          setError(
            "Some niches didn't complete — the YouTube daily quota is likely used up, or those niches are failing. Check Quota for today's usage; it resets at midnight UTC.",
          );
          break;
        }
        processed = plannedTotal - nextRemaining.length;
        remaining = nextRemaining;
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setAuto(false);
      setAutoProgress(null);
      autoRef.current = false;
    }
  };

  const pill = progress ?? autoProgress;

  return (
    <Ctx.Provider
      value={{
        busy,
        progress,
        error,
        reusedNiches,
        lastRunAt,
        runDiscovery,
        clearReused: () => setReusedNiches([]),
        mode,
        setMode,
        auto,
        autoProgress,
        runAuto,
        stopAuto,
      }}
    >
      {children}
      {(busy || auto) && pill && (
        <div className="fixed bottom-5 right-5 z-[60] flex items-center gap-2.5 rounded-full bg-slate-900 px-4 py-2.5 text-sm font-medium text-white shadow-xl">
          <svg
            className="h-4 w-4 animate-spin text-white"
            viewBox="0 0 24 24"
            fill="none"
            aria-hidden="true"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
            <path className="opacity-90" fill="currentColor" d="M4 12a8 8 0 0 1 8-8v3a5 5 0 0 0-5 5H4z" />
          </svg>
          {pill}
          {auto && (
            <button
              onClick={stopAuto}
              className="ml-1 rounded-full bg-white/15 px-2 py-0.5 text-xs font-semibold transition hover:bg-white/25"
            >
              Stop
            </button>
          )}
        </div>
      )}
    </Ctx.Provider>
  );
}

export function useDiscovery(): DiscoveryContext {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useDiscovery must be used within DiscoveryProvider");
  return ctx;
}
