"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, Overview } from "@/lib/api";
import { Card, CategoryBadge, Skeleton, StatCard, cx } from "@/components/ui";
import { NicheSelector } from "@/components/niche/NicheSelector";
import { SelectedNiche } from "@/components/niche/types";
import { useDiscovery } from "@/components/DiscoveryProvider";
import {
  FlameIcon,
  GridIcon,
  SearchIcon,
  SparklesIcon,
  TrendDownIcon,
  UsersIcon,
} from "@/components/icons";

// Opportunity tiers for the dashboard bars. "Excellent" (hot) is merged into
// "Strong", so the Strong bar's count = hot + warm.
//
// The tiers are ordinal, so the fills are one hue stepped light→dark rather than
// three separate colours: darker reads as stronger. Each row also carries a
// badge, a count and a percentage, so the tier is never colour-alone.
const TIERS: { key: string; cats: string[]; fill: string }[] = [
  { key: "strong", cats: ["hot", "warm"], fill: "#047857" },
  { key: "cold", cats: ["cold"], fill: "#10b981" },
  { key: "disqualified", cats: ["disqualified"], fill: "#6ee7b7" },
];

export default function OverviewPage() {
  const [data, setData] = useState<Overview | null>(null);
  const [niches, setNiches] = useState<SelectedNiche[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  // Reset is irreversible, so it asks once before firing.
  const [confirmReset, setConfirmReset] = useState(false);
  const [resetting, setResetting] = useState(false);
  // Discovery runs in a global provider so it keeps going across navigation.
  const {
    busy,
    progress,
    error: discoveryError,
    reusedNiches,
    lastRunAt,
    runDiscovery,
    auto,
    autoProgress,
    runAuto,
    stopAuto,
  } = useDiscovery();

  const load = async () => {
    try {
      setData(await api.overview());
      setLoadError(null);
    } catch (e) {
      setLoadError((e as Error).message);
    }
  };

  // Reload on mount and whenever a background discovery finishes (lastRunAt).
  useEffect(() => {
    load();
  }, [lastRunAt]);

  const resetDashboard = async () => {
    setResetting(true);
    try {
      await api.resetDashboard();
      setConfirmReset(false);
      setNiches([]);
      await load();
    } catch (e) {
      setLoadError((e as Error).message);
    } finally {
      setResetting(false);
    }
  };

  const error = loadError ?? discoveryError;
  const runs = data?.recent_runs ?? [];
  const totalScored = data?.total_scored ?? 0;
  const totalChannels = data?.total_channels ?? 0;
  const hasData = totalChannels > 0 || totalScored > 0;

  return (
    <div>
      {/* Header */}
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4 animate-fade-up">
        <div>
          <h1 className="text-[30px] font-semibold leading-[1.12] tracking-[-0.028em] text-slate-900">
            Overview
          </h1>
          <p className="mt-2 max-w-xl text-[15px] leading-relaxed text-slate-500">
            Discover creators, detect underperformance, and score qualified leads.
          </p>
        </div>
        {data !== null && data.retention_days ? (
          <span className="rounded-full bg-white px-3 py-1.5 text-xs font-medium text-slate-500 shadow-card">
            Records kept {data.retention_days} days
          </span>
        ) : null}
      </div>

      {/* Niche selection + discovery */}
      <div className="mb-8 animate-fade-up" style={{ animationDelay: "40ms" }} id="discovery-input">
        <Card className="p-5">
          <NicheSelector value={niches} onChange={setNiches} />
          <div className="mt-7 flex flex-wrap items-center justify-between gap-y-3">
            <div className="flex items-center gap-4">
              <span className="text-xs text-slate-400">
                {auto
                  ? autoProgress ?? "Auto mode running…"
                  : niches.length > 0
                    ? `Runs discovery for ${Math.min(niches.length, 8)} niche${niches.length === 1 ? "" : "s"}`
                    : "Select niches, or use Auto mode to sweep all of them"}
              </span>
              {/* Only offered when there is something to clear, and never mid-run. */}
              {hasData &&
                !busy &&
                !auto &&
                (confirmReset ? (
                  <span className="flex items-center gap-2 text-xs">
                    <span className="text-slate-500">Delete all {totalChannels} creators?</span>
                    <button
                      onClick={resetDashboard}
                      disabled={resetting}
                      className="focus-ring rounded-md bg-rose-600 px-2.5 py-1 font-medium text-white transition hover:bg-rose-700 disabled:opacity-50"
                    >
                      {resetting ? "Resetting…" : "Yes, reset"}
                    </button>
                    <button
                      onClick={() => setConfirmReset(false)}
                      disabled={resetting}
                      className="focus-ring rounded-md px-2 py-1 text-slate-500 transition hover:text-slate-700"
                    >
                      Cancel
                    </button>
                  </span>
                ) : (
                  <button
                    onClick={() => setConfirmReset(true)}
                    title="Delete every discovered creator and start over. Accounts and niches are kept."
                    className="focus-ring rounded-md px-2 py-1 text-xs font-medium text-slate-400 transition hover:bg-rose-50 hover:text-rose-600"
                  >
                    Reset dashboard
                  </button>
                ))}
            </div>
            <div className="flex items-center gap-3">
              {totalScored > 0 && !busy && !auto && (
                <Link
                  href="/leads"
                  className="focus-ring inline-flex items-center gap-1 rounded-lg px-3 py-2.5 text-sm font-medium text-emerald-700 transition hover:bg-emerald-50"
                >
                  View leads →
                </Link>
              )}
              <button
                onClick={() => runDiscovery(niches)}
                disabled={busy || auto || niches.length === 0}
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
              {/* Auto mode: sweep all not-recently-run niches, 8 at a time. */}
              <button
                onClick={auto ? stopAuto : runAuto}
                disabled={busy}
                title="Automatically discover every niche that hasn't been run in the last 24h, 8 at a time"
                className={cx(
                  "focus-ring inline-flex items-center justify-center gap-2 rounded-lg px-5 py-2.5 text-sm font-medium shadow-sm transition duration-150 ease-out active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50",
                  auto
                    ? "bg-rose-600 text-white hover:bg-rose-700"
                    : "border border-slate-300 bg-white text-slate-700 hover:border-slate-400 hover:bg-slate-50",
                )}
              >
                {auto ? (
                  <>
                    <Spinner />
                    Stop auto
                  </>
                ) : (
                  <>
                    <SparklesIcon className="h-4 w-4" />
                    Auto mode
                  </>
                )}
              </button>
            </div>
          </div>
        </Card>
      </div>

      {error && (
        <div className="mb-6 animate-fade-up rounded-r-lg border-l-[3px] border-rose-400 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      {reusedNiches.length > 0 && !busy && (
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-r-lg border-l-[3px] border-amber-400 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <span>
            {reusedNiches.join(", ")} {reusedNiches.length === 1 ? "was" : "were"}{" "}
            discovered recently — showing those results to save API quota.
          </span>
          <button
            onClick={() => runDiscovery(niches, true)}
            className="focus-ring shrink-0 rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-xs font-medium text-amber-800 transition hover:bg-amber-100"
          >
            Run fresh anyway
          </button>
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
              href="/leads?scope=all"
            />
            <StatCard
              label="Scored"
              value={totalScored}
              icon={<UsersIcon className="h-4 w-4" />}
              series={runs.map((r) => r.discovered)}
              href="/leads?scope=all"
            />
            <StatCard
              label="Underperforming"
              value={data.underperforming}
              icon={<TrendDownIcon className="h-4 w-4" />}
              series={runs.map((r) => r.underperforming)}
              href="/leads?scope=all&underperforming=1"
            />
            <StatCard
              label="Strong matches"
              value={(data.by_category?.hot ?? 0) + (data.by_category?.warm ?? 0)}
              icon={<FlameIcon className="h-4 w-4" />}
              series={runs.map((r) => r.hot)}
              href="/leads?scope=all&category=strong"
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
              <h2 className="text-[15px] font-semibold tracking-[-0.01em] text-slate-900">
                AI Opportunity Analysis
              </h2>
              <p className="mt-1 text-xs leading-relaxed text-slate-400">
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
              {TIERS.map((tier) => {
                const count = tier.cats.reduce(
                  (sum, c) => sum + (data.by_category?.[c] ?? 0),
                  0,
                );
                const pct = totalScored ? Math.round((count / totalScored) * 100) : 0;
                return (
                  <Link
                    key={tier.key}
                    href={`/leads?category=${tier.key}`}
                    className="focus-ring group -mx-2 flex items-center gap-4 rounded-lg px-2 py-2 transition hover:bg-slate-50"
                  >
                    <div className="w-36">
                      <CategoryBadge category={tier.key} />
                    </div>
                    <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-slate-100">
                      <div
                        className="h-full rounded-full transition-[width] duration-700 ease-out"
                        style={{ width: `${pct}%`, backgroundColor: tier.fill }}
                      />
                    </div>
                    <div className="flex w-20 items-center justify-end gap-2 text-sm tabular-nums">
                      <span className="font-semibold text-slate-900">{count}</span>
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
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-50 text-emerald-500">
        <SearchIcon className="h-5 w-5" />
      </div>
      <p className="mt-4 text-sm font-semibold text-slate-700">Nothing scored yet</p>
      <p className="mt-1.5 max-w-sm text-sm leading-relaxed text-slate-400">
        Pick a niche and run discovery. Scored creators appear here, grouped by how
        strong a match they are.
      </p>
    </div>
  );
}
