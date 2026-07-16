"use client";

import { createContext, useContext, useRef, useState, ReactNode } from "react";
import { api, setLastDiscovery } from "@/lib/api";
import { SelectedNiche } from "@/components/niche/types";

interface DiscoveryContext {
  busy: boolean;
  progress: string | null;
  error: string | null;
  reusedNiches: string[];
  lastRunAt: number; // bumped each time a run finishes; pages watch it to refresh
  runDiscovery: (niches: SelectedNiche[], force?: boolean) => Promise<void>;
  clearReused: () => void;
}

const Ctx = createContext<DiscoveryContext | null>(null);

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
  const runningRef = useRef(false);

  const runDiscovery = async (niches: SelectedNiche[], force = false) => {
    if (niches.length === 0 || runningRef.current) return;
    runningRef.current = true;
    setBusy(true);
    setError(null);
    setReusedNiches([]);
    const targets = niches.slice(0, 8);
    try {
      const runIds: string[] = [];
      const reused: string[] = [];
      for (let i = 0; i < targets.length; i++) {
        setProgress(`Discovering ${i + 1}/${targets.length} · ${targets[i].name}`);
        const run = await api.runPipeline(targets[i].name, 20, force);
        if (run?.id) runIds.push(run.id);
        if (run?.reused) reused.push(targets[i].name);
      }
      setLastDiscovery(
        runIds,
        targets.map((t) => t.name),
      );
      setReusedNiches(reused);
      setLastRunAt(Date.now());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
      setProgress(null);
      runningRef.current = false;
    }
  };

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
      }}
    >
      {children}
      {busy && (
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
          {progress ?? "Discovering…"}
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
