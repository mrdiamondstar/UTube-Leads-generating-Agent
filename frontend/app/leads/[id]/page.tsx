"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, LeadDetail } from "@/lib/api";
import {
  Avatar,
  Card,
  CategoryBadge,
  cx,
  formatNumber,
  timeAgo,
} from "@/components/ui";
import { ContactLinks } from "@/components/ContactLinks";
import {
  ArrowLeftIcon,
  ChatIcon,
  ExternalLinkIcon,
  EyeIcon,
  HeartIcon,
} from "@/components/icons";

const FEATURE_LABELS: Record<string, string> = {
  opportunity_gap: "Opportunity gap",
  audience_size: "Audience size",
  reachability: "Reachability",
  content_volume: "Content volume",
};

export default function ChannelDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<LeadDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    api.leadDetail(id).then(setData).catch((e) => setError((e as Error).message));
  }, [id]);

  if (error) {
    return (
      <div>
        <BackLink />
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div>
        <BackLink />
        <p className="mt-8 text-sm text-slate-400">Loading channel…</p>
      </div>
    );
  }

  const { channel, score, videos } = data;
  const contributions = score?.feature_contributions ?? {};

  return (
    <div>
      <BackLink />

      {/* Header */}
      <Card className="mt-4 p-6">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-4">
            <div className="scale-125">
              <Avatar name={channel.title} />
            </div>
            <div>
              <a
                href={channel.youtube_url}
                target="_blank"
                rel="noreferrer"
                className="group inline-flex items-center gap-1.5 text-xl font-semibold text-slate-900 hover:text-emerald-700"
              >
                {channel.title}
                <ExternalLinkIcon className="h-4 w-4 text-slate-300 group-hover:text-emerald-600" />
              </a>
              <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-slate-500">
                <span>{channel.country_name ?? channel.country ?? "—"}</span>
                {channel.category && (
                  <>
                    <span className="text-slate-300">·</span>
                    <span>{channel.category}</span>
                  </>
                )}
              </div>
              <div className="mt-2">
                <ContactLinks
                  email={channel.public_email}
                  website={channel.website}
                  socials={channel.social_links}
                />
              </div>
            </div>
          </div>
          {score && (
            <div className="text-right">
              <div className="text-4xl font-semibold tracking-tight text-slate-900">
                {score.score.toFixed(0)}
                <span className="text-lg text-slate-300">/100</span>
              </div>
              <div className="mt-1 flex items-center justify-end gap-2">
                <CategoryBadge category={score.category} />
                {score.is_underperforming && (
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
                    Underperforming
                  </span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* KPI strip */}
        <div className="mt-6 grid grid-cols-3 gap-4 border-t border-slate-100 pt-5">
          <Kpi label="Subscribers" value={formatNumber(channel.subscriber_count)} />
          <Kpi label="Total views" value={formatNumber(channel.view_count)} />
          <Kpi label="Videos" value={formatNumber(channel.video_count)} />
        </div>
      </Card>

      <div className="mt-6 grid gap-6 lg:grid-cols-5">
        {/* Score breakdown */}
        <Card className="p-6 lg:col-span-2">
          <h2 className="text-sm font-semibold text-slate-900">Score breakdown</h2>
          {score ? (
            <>
              <div className="mt-5 space-y-4">
                {Object.entries(contributions).map(([key, c]) => (
                  <div key={key}>
                    <div className="mb-1 flex items-center justify-between text-sm">
                      <span className="text-slate-600">
                        {FEATURE_LABELS[key] ?? key}
                      </span>
                      <span className="tabular-nums font-medium text-slate-900">
                        +{c.contribution.toFixed(1)} pts
                      </span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                      <div
                        className="h-full rounded-full bg-emerald-500"
                        style={{ width: `${Math.round(c.strength * 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-4 text-sm">
                <span className="text-slate-500">Confidence</span>
                <span className="font-medium text-slate-900">
                  {Math.round(score.confidence * 100)}%
                </span>
              </div>
              {score.reasoning && (
                <p className="mt-4 rounded-lg bg-slate-50 p-3 text-xs leading-relaxed text-slate-500">
                  {score.reasoning}
                </p>
              )}
            </>
          ) : (
            <p className="mt-4 text-sm text-slate-400">No score available.</p>
          )}
        </Card>

        {/* Recent videos */}
        <Card className="p-6 lg:col-span-3">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">Recent videos</h2>
            <span className="text-xs text-slate-400">{videos.length} tracked</span>
          </div>
          {videos.length === 0 ? (
            <p className="py-6 text-center text-sm text-slate-400">
              No videos captured for this channel yet.
            </p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {videos.map((v) => (
                <li key={v.id} className="py-3 first:pt-0 last:pb-0">
                  <a
                    href={v.youtube_url}
                    target="_blank"
                    rel="noreferrer"
                    className="line-clamp-1 text-sm font-medium text-slate-800 hover:text-emerald-700 hover:underline"
                    title={v.title}
                  >
                    {v.title}
                  </a>
                  <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-400">
                    <Stat icon={<EyeIcon className="h-3.5 w-3.5" />} value={formatNumber(v.view_count)} />
                    <Stat icon={<HeartIcon className="h-3.5 w-3.5" />} value={formatNumber(v.like_count)} />
                    <Stat icon={<ChatIcon className="h-3.5 w-3.5" />} value={formatNumber(v.comment_count)} />
                    <span className="text-slate-300">·</span>
                    <span>{timeAgo(v.published_at)}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}

function BackLink() {
  return (
    <Link
      href="/leads"
      className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-slate-900"
    >
      <ArrowLeftIcon className="h-4 w-4" />
      Back to leads
    </Link>
  );
}

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xl font-semibold text-slate-900">{value}</div>
      <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
    </div>
  );
}

function Stat({ icon, value }: { icon: React.ReactNode; value: string }) {
  return (
    <span className={cx("inline-flex items-center gap-1")}>
      {icon}
      {value}
    </span>
  );
}
