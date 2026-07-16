"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, Overview, setLastDiscovery } from "@/lib/api";
import { Card, CategoryBadge, Skeleton, StatCard, cx } from "@/components/ui";
import { NicheSelector } from "@/components/niche/NicheSelector";
import { SelectedNiche } from "@/components/niche/types";
import {
  FlameIcon,
  GridIcon,
  SearchIcon,
  TrendDownIcon,
  UsersIcon,
} from "@/components/icons";

const CATEGORY_ORDER = ["hot", "warm", "cold", "disqualified"];
const CATEGORY_META: Record<string, { bar: string; label: string }> = {
  hot: { bar: "bg-emerald-400", label: "Excellent Match" },
  warm: { bar: "bg-sky-400", label: "Strong Match" },
  cold: { bar: "bg-amber-400", label: "Moderate Match" },
  disqualified: { bar: "bg-rose-300", label: "Low Match" },
};

export default function OverviewPage() {
  const [data, setData] = useState<Overview | null>(null);
  const [niches, setNiches] = useState<SelectedNiche[]>([]);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setData(await api.overview());
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const runPipeline = async () => {
    if (niches.length === 0) return;
    setBusy(true);
    setError(null);
    // Discover across each selected niche (capped to protect API quota).
    const targets = niches.slice(0, 8);
    try {
      const runIds: string[] = [];
      for (let i = 0; i < targets.length; i++) {
        setProgress(`Discovering ${i + 1}/${targets.length} · ${targets[i].name}`);
        const run = await api.runPipeline(targets[i].name, 20);
        if (run?.id) runIds.push(run.id);
      }
      // Remember exactly THIS discovery (its run ids) so the Leads page shows
      // only these results — never previous searches. Persists across refresh.
      setLastDiscovery(runIds, targets.map((t) => t.name));
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
      setProgress(null);
    }
  };

  const runs = data?.recent_runs ?? [];
  const totalScored = data?.total_scored ?? 0;

  return (
    <div>
      {/* Header */}
      <div className="mb-8 animate-fade-up">
        <h1 className="text-[26px] font-semibold leading-tight text-slate-900">Overview</h1>
        <p className="mt-1.5 text-sm text-slate-500">
          Discover creators, detect underperformance, and score qualified leads.
        </p>
      </div>

      {/* Niche selection + discovery */}
      <div className="mb-8 animate-fade-up" style={{ animationDelay: "40ms" }} id="discovery-input">
        <Card className="p-5">
          <NicheSelector value={niches} onChange={setNiches} />
          <div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-4">
            <span className="text-xs text-slate-400">
              {niches.length > 0
                ? `Runs discovery for ${Math.min(niches.length, 8)} niche${niches.length === 1 ? "" : "s"}`
                : "Select at least one niche to begin"}
            </span>
            <div className="flex items-center gap-3">
              {totalScored > 0 && !busy && (
                <Link
                  href="/leads"
                  className="focus-ring inline-flex items-center gap-1 rounded-lg px-3 py-2.5 text-sm font-medium text-emerald-700 transition hover:bg-emerald-50"
                >
                  View leads →
                </Link>
              )}
              <button
                onClick={runPipeline}
                disabled={busy || niches.length === 0}
                className="focus-ring inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition duration-150 ease-out hover:bg-emerald-700 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {busy ? (
                  <>
                    <Spinner />
                    {progress ?? "Discovering…"}
                  </>
                ) : (
                  "Run discovery"
                )}
              </button>
            </div>
          </div>
        </Card>
      </div>

      {error && (
        <div className="mb-6 animate-fade-up rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      {/* Metric cards */}
      <div
        className="grid animate-fade-up grid-cols-2 gap-4 lg:grid-cols-4"
        style={{ animationDelay: "80ms" }}
      >
        {data === null ? (
          Array.from({ length: 4 }).map((_, i) => <StatSkeleton key={i} />)
        ) : (
          <>
            <StatCard
              label="Channels"
              value={data.total_channels}
              icon={<GridIcon className="h-4 w-4" />}
              series={runs.map((r) => r.discovered)}
            />
            <StatCard
              label="Scored"
              value={totalScored}
              icon={<UsersIcon className="h-4 w-4" />}
              series={runs.map((r) => r.discovered)}
            />
            <StatCard
              label="Underperforming"
              value={data.underperforming}
              icon={<TrendDownIcon className="h-4 w-4" />}
              series={runs.map((r) => r.underperforming)}
            />
            <StatCard
              label="Excellent matches"
              value={data.by_category?.hot ?? 0}
              icon={<FlameIcon className="h-4 w-4" />}
              series={runs.map((r) => r.hot)}
              accent
            />
          </>
        )}
      </div>

      {/* Lead distribution */}
      <div className="mt-6 animate-fade-up" style={{ animationDelay: "120ms" }}>
        <Card className="p-6">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">AI Opportunity Analysis</h2>
              <p className="mt-0.5 text-xs text-slate-400">
                Scored creators grouped by opportunity match — click a tier to view its leads
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span className="rounded-full bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-500">
                {totalScored} scored
              </span>
              {totalScored > 0 && (
                <Link
                  href="/leads"
                  className="focus-ring inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:border-emerald-300 hover:text-emerald-700"
                >
                  View leads →
                </Link>
              )}
            </div>
          </div>

          {data === null ? (
            <div className="space-y-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-6 w-full" />
              ))}
            </div>
          ) : totalScored === 0 ? (
            <EmptyDistribution />
          ) : (
            <div className="space-y-2">
              {CATEGORY_ORDER.map((cat) => {
                const count = data.by_category?.[cat] ?? 0;
                const pct = totalScored ? Math.round((count / totalScored) * 100) : 0;
                return (
                  <Link
                    key={cat}
                    href={`/leads?category=${cat}`}
                    className="focus-ring group -mx-2 flex items-center gap-4 rounded-lg px-2 py-2 transition hover:bg-slate-50"
                  >
                    <div className="w-36">
                      <CategoryBadge category={cat} />
                    </div>
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                      <div
                        className={cx(
                          "h-full rounded-full transition-[width] duration-700 ease-out",
                          CATEGORY_META[cat].bar,
                        )}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <div className="flex w-20 items-center justify-end gap-2 text-sm tabular-nums">
                      <span className="font-medium text-slate-900">{count}</span>
                      <span className="text-slate-400">{pct}%</span>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

function Spinner() {
  return (
    <svg className="h-4 w-4 animate-spin text-white" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
      <path className="opacity-90" fill="currentColor" d="M4 12a8 8 0 0 1 8-8v3a5 5 0 0 0-5 5H4z" />
    </svg>
  );
}

function StatSkeleton() {
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between">
        <Skeleton className="h-3.5 w-20" />
        <Skeleton className="h-8 w-8 rounded-lg" />
      </div>
      <div className="mt-4 flex items-end justify-between">
        <div className="space-y-2">
          <Skeleton className="h-7 w-16" />
          <Skeleton className="h-3 w-10" />
        </div>
        <Skeleton className="h-7 w-[72px]" />
      </div>
    </Card>
  );
}

function EmptyDistribution() {
  return (
    <div className="flex flex-col items-center justify-center py-10 text-center">
      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-slate-50 text-slate-300">
        <SearchIcon className="h-5 w-5" />
      </div>
      <p className="mt-3 text-sm font-medium text-slate-600">No leads yet</p>
      <p className="mt-1 text-sm text-slate-400">
        Run a discovery above to populate the dashboard.
      </p>
    </div>
  );
}
