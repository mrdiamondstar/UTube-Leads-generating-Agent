"use client";

import Link from "next/link";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  api,
  API_BASE,
  Lead,
  LeadStatus,
  LEAD_STATUSES,
  getLastDiscovery,
  leadsQuery,
} from "@/lib/api";
import {
  Avatar,
  Card,
  CategoryBadge,
  PageHeader,
  ScoreBar,
  categoryLabel,
  cx,
  formatNumber,
  timeAgo,
} from "@/components/ui";
import { ContactLinks } from "@/components/ContactLinks";
import { DownloadIcon, ExternalLinkIcon } from "@/components/icons";

const STATUS_FILTERS = ["all", ...LEAD_STATUSES] as const;

// Opportunity-match filter tiers (raw value -> product-facing label).
// "strong" is a merged tier = Excellent + Strong (hot + warm).
const MATCH_FILTERS: { value: string; label: string }[] = [
  { value: "all", label: "All" },
  { value: "strong", label: "Strong Match" },
  { value: "cold", label: "Moderate Match" },
  { value: "disqualified", label: "Low Match" },
];
const MATCH_VALUES = ["strong", "cold", "disqualified"];

// Colour treatment per outreach status (used by the row dropdown).
const STATUS_STYLES: Record<LeadStatus, { pill: string; dot: string }> = {
  active: { pill: "bg-blue-50 text-blue-700 ring-blue-600/20", dot: "bg-blue-500" },
  interested: {
    pill: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
    dot: "bg-emerald-500",
  },
  closed: { pill: "bg-slate-100 text-slate-600 ring-slate-500/20", dot: "bg-slate-400" },
  rejected: { pill: "bg-rose-50 text-rose-700 ring-rose-600/20", dot: "bg-rose-500" },
};

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [category, setCategory] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [underperforming, setUnderperforming] = useState(false);
  const [runIds, setRunIds] = useState<string[]>([]);
  const [niches, setNiches] = useState<string[]>([]);
  const [scope, setScope] = useState<"last" | "all">("all");
  const [hydrated, setHydrated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load the last discovery + any URL filters (from dashboard card clicks) once
  // on mount. `hydrated` gates the fetch so we never fire an unfiltered request
  // first (which could resolve late and clobber the filtered results).
  useEffect(() => {
    const last = getLastDiscovery();
    setRunIds(last.runIds);
    setNiches(last.niches);
    const params = new URLSearchParams(window.location.search);
    const urlCategory = params.get("category");
    // Map legacy links (?category=hot|warm) onto the merged "strong" tier.
    const normalized =
      urlCategory === "hot" || urlCategory === "warm" ? "strong" : urlCategory;
    if (normalized && MATCH_VALUES.includes(normalized)) setCategory(normalized);
    if (params.get("underperforming") === "1") setUnderperforming(true);
    // Dashboard cards link with ?scope=all to show the whole dataset, not just
    // the last discovery.
    if (params.get("scope") === "all") {
      setScope("all");
    } else {
      setScope(last.runIds.length > 0 ? "last" : "all");
    }
    setHydrated(true);
  }, []);

  const activeRunIds = scope === "last" && runIds.length > 0 ? runIds : undefined;

  useEffect(() => {
    if (!hydrated) return;
    let cancelled = false;
    setLoading(true);
    api
      .leads(
        category === "all" ? undefined : category,
        activeRunIds,
        statusFilter === "all" ? undefined : statusFilter,
        underperforming,
      )
      .then((d) => {
        if (cancelled) return;
        setLeads(d);
        setError(null);
      })
      .catch((e) => {
        if (!cancelled) setError((e as Error).message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hydrated, category, statusFilter, underperforming, scope, runIds]);

  // Change a lead's outreach status (optimistic; reverts on error).
  const updateStatus = async (channelId: string, next: LeadStatus) => {
    const prev = leads;
    setLeads((cur) =>
      cur.map((l) =>
        l.channel.id === channelId ? { ...l, status: next } : l,
      ),
    );
    try {
      await api.setLeadStatus(channelId, next);
      // If filtering by a status, drop rows that no longer match.
      if (statusFilter !== "all" && next !== statusFilter) {
        setLeads((cur) => cur.filter((l) => l.channel.id !== channelId));
      }
    } catch (e) {
      setLeads(prev); // revert
      setError((e as Error).message);
    }
  };

  const exportHref = `${API_BASE}/api/v1/leads/export${leadsQuery(
    category === "all" ? undefined : category,
    activeRunIds,
  )}`;

  return (
    <div>
      <PageHeader
        title="Leads"
        subtitle={
          activeRunIds
            ? `Showing only your last discovery${
                niches.length > 0 ? `: ${niches.join(", ")}` : ""
              }.`
            : "Ranked by opportunity score. Excluded regions are disqualified automatically."
        }
        actions={
          <a
            href={exportHref}
            className="focus-ring inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-700"
          >
            <DownloadIcon className="h-[18px] w-[18px]" />
            Export Excel
          </a>
        }
      />

      {/* Scope toggle: current discovery vs. all leads */}
      {runIds.length > 0 && (
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-slate-400">Scope</span>
          <button
            onClick={() => setScope("last")}
            className={cx(
              "focus-ring rounded-full px-3.5 py-1.5 text-xs font-medium transition",
              scope === "last"
                ? "bg-emerald-600 text-white"
                : "border border-slate-200 bg-white text-slate-600 hover:border-slate-300",
            )}
          >
            {niches.length > 0
              ? `Last discovery (${niches.join(", ")})`
              : "Last discovery"}
          </button>
          <button
            onClick={() => setScope("all")}
            className={cx(
              "focus-ring rounded-full px-3.5 py-1.5 text-xs font-medium transition",
              scope === "all"
                ? "bg-emerald-600 text-white"
                : "border border-slate-200 bg-white text-slate-600 hover:border-slate-300",
            )}
          >
            All leads
          </button>
        </div>
      )}

      {/* Opportunity match filter chips */}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-slate-400">Match</span>
        {MATCH_FILTERS.map((m) => (
          <button
            key={m.value}
            onClick={() => setCategory(m.value)}
            className={cx(
              "focus-ring rounded-full px-3.5 py-1.5 text-xs font-medium transition",
              category === m.value
                ? "bg-slate-900 text-white"
                : "border border-slate-200 bg-white text-slate-600 hover:border-slate-300",
            )}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Status filter chips */}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-slate-400">Status</span>
        {STATUS_FILTERS.map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={cx(
              "focus-ring rounded-full px-3.5 py-1.5 text-xs font-medium capitalize transition",
              statusFilter === s
                ? "bg-slate-900 text-white"
                : "border border-slate-200 bg-white text-slate-600 hover:border-slate-300",
            )}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Underperforming toggle */}
      <div className="mb-5 flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-slate-400">More</span>
        <button
          onClick={() => setUnderperforming((v) => !v)}
          className={cx(
            "focus-ring rounded-full px-3.5 py-1.5 text-xs font-medium transition",
            underperforming
              ? "bg-slate-900 text-white"
              : "border border-slate-200 bg-white text-slate-600 hover:border-slate-300",
          )}
        >
          Underperforming only
        </button>
      </div>

      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error} — run a discovery from the Overview page first.
        </div>
      )}

      <p className="mb-3 text-xs text-slate-400">
        Score and Match are Creator Intelligence Platform&apos;s own analysis — not YouTube
        metrics. Subscriber counts are as reported by YouTube.
      </p>

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-400">
                <th className="px-5 py-3">Channel</th>
                <th className="px-5 py-3">Niche</th>
                <th className="px-5 py-3">Country</th>
                <th className="px-5 py-3">Subscribers</th>
                <th className="px-5 py-3">Score</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3 min-w-[240px]">Latest video</th>
                <th className="px-5 py-3">Contact details</th>
                <th className="px-5 py-3">Match</th>
                <th className="px-5 py-3">Analysis</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {leads.map(({ channel, score, latest_video, niche, status }) => (
                <tr key={channel.id} className="transition hover:bg-slate-50/70">
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-3">
                      <Avatar name={channel.title} />
                      <div className="min-w-0">
                        <a
                          href={channel.youtube_url}
                          target="_blank"
                          rel="noreferrer"
                          className="group flex items-center gap-1 font-medium text-slate-900 hover:text-emerald-700"
                        >
                          <span className="truncate">{channel.title}</span>
                          <ExternalLinkIcon className="h-3.5 w-3.5 flex-shrink-0 text-slate-300 group-hover:text-emerald-600" />
                        </a>
                        <div className="text-xs text-slate-400">
                          {channel.category ?? "—"}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-5 py-3">
                    {niche ? (
                      <span className="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
                        {niche}
                      </span>
                    ) : (
                      <span className="text-slate-300">—</span>
                    )}
                  </td>
                  <td className="px-5 py-3 text-slate-600">
                    {channel.country_name ?? channel.country ?? "—"}
                  </td>
                  <td className="px-5 py-3 tabular-nums text-slate-600">
                    {formatNumber(channel.subscriber_count)}
                  </td>
                  <td className="px-5 py-3">
                    <ScoreBar score={score.score} />
                  </td>
                  <td className="px-5 py-3">
                    <StatusSelect
                      value={status}
                      onChange={(next) => updateStatus(channel.id, next)}
                    />
                  </td>
                  <td className="px-5 py-3">
                    {latest_video ? (
                      <div className="max-w-xs">
                        <a
                          href={latest_video.youtube_url}
                          target="_blank"
                          rel="noreferrer"
                          className="line-clamp-1 font-medium text-slate-700 hover:text-emerald-700 hover:underline"
                          title={latest_video.title}
                        >
                          {latest_video.title}
                        </a>
                        <div className="mt-0.5 text-xs text-slate-400">
                          {formatNumber(latest_video.view_count)} views ·{" "}
                          {timeAgo(latest_video.published_at)}
                        </div>
                      </div>
                    ) : (
                      <span className="text-slate-300">—</span>
                    )}
                  </td>
                  <td className="px-5 py-3">
                    <ContactLinks
                      email={channel.public_email}
                      website={channel.website}
                      socials={channel.social_links}
                    />
                  </td>
                  <td className="px-5 py-3">
                    <CategoryBadge category={score.category} />
                  </td>
                  <td className="px-5 py-3">
                    <Link
                      href={`/leads/${channel.id}`}
                      className="focus-ring inline-flex items-center whitespace-nowrap rounded-lg border border-emerald-600 px-3 py-1.5 text-xs font-medium text-emerald-700 transition hover:bg-emerald-600 hover:text-white"
                    >
                      View analysis
                    </Link>
                  </td>
                </tr>
              ))}

              {!loading && leads.length === 0 && !error && (
                <tr>
                  <td colSpan={10} className="px-5 py-16 text-center">
                    <p className="text-sm font-medium text-slate-500">No leads yet</p>
                    <p className="mt-1 text-sm text-slate-400">
                      {activeRunIds
                        ? "No leads from your last discovery. Switch to “All leads” above, or run a new discovery."
                        : "Run a discovery from the Overview page to populate this table."}
                    </p>
                  </td>
                </tr>
              )}

              {loading && (
                <tr>
                  <td colSpan={10} className="px-5 py-16 text-center text-sm text-slate-400">
                    Loading leads…
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {leads.length > 0 && (
        <p className="mt-3 text-xs text-slate-400">
          Showing {leads.length} lead{leads.length === 1 ? "" : "s"}
          {category !== "all" ? ` · ${categoryLabel(category)}` : ""}
          {statusFilter !== "all" ? ` · status “${statusFilter}”` : ""}
          {activeRunIds && niches.length > 0 ? ` for ${niches.join(", ")}` : ""}.
        </p>
      )}
    </div>
  );
}

/**
 * Inline outreach-status picker for a lead row (defaults to Active).
 *
 * A custom dropdown — not a native <select> — so the menu itself is fully
 * styled (coloured status dots, soft shadow, hover states, a check on the
 * current value). The menu renders through a portal with fixed positioning so
 * it's never clipped by the table's horizontal-scroll container.
 */
function StatusSelect({
  value,
  onChange,
}: {
  value: LeadStatus;
  onChange: (next: LeadStatus) => void;
}) {
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState<{ top: number; left: number; width: number } | null>(
    null,
  );
  const btnRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const place = () => {
    const el = btnRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    setCoords({ top: r.bottom + 6, left: r.left, width: Math.max(r.width, 168) });
  };

  useLayoutEffect(() => {
    if (!open) return;
    place();
    const close = () => setOpen(false);
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    const onDown = (e: MouseEvent) => {
      const t = e.target as Node;
      if (btnRef.current?.contains(t) || menuRef.current?.contains(t)) return;
      setOpen(false);
    };
    // Reposition on scroll/resize; close if the trigger scrolls away is fine too.
    window.addEventListener("scroll", place, true);
    window.addEventListener("resize", close);
    window.addEventListener("keydown", onKey);
    window.addEventListener("mousedown", onDown);
    return () => {
      window.removeEventListener("scroll", place, true);
      window.removeEventListener("resize", close);
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("mousedown", onDown);
    };
  }, [open]);

  const style = STATUS_STYLES[value];

  return (
    <>
      <button
        ref={btnRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label="Lead status"
        className={cx(
          "focus-ring inline-flex items-center gap-1.5 rounded-full py-1.5 pl-2.5 pr-2 text-xs font-medium capitalize ring-1 ring-inset transition",
          style.pill,
        )}
      >
        <span className={cx("h-1.5 w-1.5 rounded-full", style.dot)} />
        {value}
        <svg
          className={cx("h-3 w-3 opacity-60 transition-transform", open && "rotate-180")}
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 011.06.02L10 11.06l3.71-3.83a.75.75 0 111.08 1.04l-4.25 4.39a.75.75 0 01-1.08 0L5.21 8.27a.75.75 0 01.02-1.06z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {open &&
        coords &&
        createPortal(
          <div
            ref={menuRef}
            role="listbox"
            style={{ top: coords.top, left: coords.left, minWidth: coords.width }}
            className="fixed z-50 origin-top overflow-hidden rounded-xl border border-slate-200/80 bg-white p-1 shadow-card-lg animate-fade-up"
          >
            {LEAD_STATUSES.map((s) => {
              const selected = s === value;
              const st = STATUS_STYLES[s];
              return (
                <button
                  key={s}
                  type="button"
                  role="option"
                  aria-selected={selected}
                  onClick={() => {
                    onChange(s);
                    setOpen(false);
                  }}
                  className={cx(
                    "flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-xs font-medium capitalize transition",
                    selected ? "bg-slate-50 text-slate-900" : "text-slate-600 hover:bg-slate-50",
                  )}
                >
                  <span className={cx("h-2 w-2 rounded-full", st.dot)} />
                  <span className="flex-1">{s}</span>
                  {selected && (
                    <svg
                      className="h-3.5 w-3.5 text-emerald-600"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                      aria-hidden="true"
                    >
                      <path
                        fillRule="evenodd"
                        d="M16.7 5.3a1 1 0 010 1.4l-7.5 7.5a1 1 0 01-1.4 0l-3.5-3.5a1 1 0 011.4-1.4l2.8 2.79 6.8-6.79a1 1 0 011.4 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                  )}
                </button>
              );
            })}
          </div>,
          document.body,
        )}
    </>
  );
}
