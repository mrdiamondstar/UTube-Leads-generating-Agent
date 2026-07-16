"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, API_BASE, Lead, getLastNiches, leadsQuery } from "@/lib/api";
import { Avatar, Card, CategoryBadge, PageHeader, ScoreBar, cx, formatNumber, timeAgo } from "@/components/ui";
import { ContactLinks } from "@/components/ContactLinks";
import { DownloadIcon, ExternalLinkIcon } from "@/components/icons";

const CATEGORIES = ["all", "hot", "warm", "cold", "disqualified"] as const;

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [category, setCategory] = useState<string>("all");
  const [niches, setNiches] = useState<string[]>([]);
  const [scope, setScope] = useState<"last" | "all">("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load the last-run niches once on mount; default to showing only those.
  useEffect(() => {
    const last = getLastNiches();
    setNiches(last);
    setScope(last.length > 0 ? "last" : "all");
  }, []);

  const activeNiches = scope === "last" && niches.length > 0 ? niches : undefined;

  useEffect(() => {
    setLoading(true);
    api
      .leads(category === "all" ? undefined : category, activeNiches)
      .then((d) => {
        setLeads(d);
        setError(null);
      })
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [category, scope, niches]);

  const exportHref = `${API_BASE}/api/v1/leads/export${leadsQuery(
    category === "all" ? undefined : category,
    activeNiches,
  )}`;

  return (
    <div>
      <PageHeader
        title="Leads"
        subtitle={
          activeNiches
            ? `Showing leads from your last discovery: ${activeNiches.join(", ")}.`
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

      {/* Scope toggle: last-discovery niches vs. all leads */}
      {niches.length > 0 && (
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
            Last discovery ({niches.join(", ")})
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

      {/* Filter chips */}
      <div className="mb-5 flex flex-wrap gap-2">
        {CATEGORIES.map((c) => (
          <button
            key={c}
            onClick={() => setCategory(c)}
            className={cx(
              "focus-ring rounded-full px-3.5 py-1.5 text-xs font-medium capitalize transition",
              category === c
                ? "bg-slate-900 text-white"
                : "border border-slate-200 bg-white text-slate-600 hover:border-slate-300",
            )}
          >
            {c}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error} — run a discovery from the Overview page first.
        </div>
      )}

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-400">
                <th className="px-5 py-3">Channel</th>
                <th className="px-5 py-3">Country</th>
                <th className="px-5 py-3">Subscribers</th>
                <th className="px-5 py-3">Score</th>
                <th className="px-5 py-3">Category</th>
                <th className="px-5 py-3 min-w-[240px]">Latest video</th>
                <th className="px-5 py-3">Contact details</th>
                <th className="px-5 py-3">Analysis</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {leads.map(({ channel, score, latest_video }) => (
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
                    <CategoryBadge category={score.category} />
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
                  <td colSpan={8} className="px-5 py-16 text-center">
                    <p className="text-sm font-medium text-slate-500">No leads yet</p>
                    <p className="mt-1 text-sm text-slate-400">
                      {activeNiches
                        ? `No leads for ${activeNiches.join(", ")}. Switch to “All leads” above, or run a new discovery.`
                        : "Run a discovery from the Overview page to populate this table."}
                    </p>
                  </td>
                </tr>
              )}

              {loading && (
                <tr>
                  <td colSpan={8} className="px-5 py-16 text-center text-sm text-slate-400">
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
          {category !== "all" ? ` in “${category}”` : ""}
          {activeNiches ? ` for ${activeNiches.join(", ")}` : ""}.
        </p>
      )}
    </div>
  );
}
