"use client";

import React, { useEffect, useRef, useState } from "react";

// --- helpers ---------------------------------------------------------------
export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

export function formatNumber(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(n % 1_000_000 === 0 ? 0 : 1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(n % 1_000 === 0 ? 0 : 1) + "K";
  return n.toLocaleString();
}

export function timeAgo(iso: string | null): string {
  if (!iso) return "—";
  const secs = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (secs < 0) return "just now";
  const units: [string, number][] = [
    ["year", 31536000],
    ["month", 2592000],
    ["week", 604800],
    ["day", 86400],
    ["hour", 3600],
    ["minute", 60],
  ];
  for (const [name, span] of units) {
    const v = Math.floor(secs / span);
    if (v >= 1) return `${v} ${name}${v > 1 ? "s" : ""} ago`;
  }
  return "just now";
}

// --- Animated counter ------------------------------------------------------
export function Counter({ value, format = formatNumber }: { value: number; format?: (n: number) => string }) {
  const [display, setDisplay] = useState(0);
  const prev = useRef(0);

  useEffect(() => {
    const from = prev.current;
    const to = value;
    prev.current = value;
    if (from === to) {
      setDisplay(to);
      return;
    }
    const duration = 700;
    const start = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3); // easeOutCubic
      setDisplay(Math.round(from + (to - from) * eased));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value]);

  return <>{format(display)}</>;
}

// --- Sparkline (pure SVG, real data) ---------------------------------------
export function Sparkline({
  data,
  width = 72,
  height = 28,
  className,
}: {
  data: number[];
  width?: number;
  height?: number;
  className?: string;
}) {
  if (!data || data.length < 2) {
    return (
      <svg width={width} height={height} className={className} aria-hidden="true">
        <line
          x1="0"
          y1={height / 2}
          x2={width}
          y2={height / 2}
          stroke="currentColor"
          strokeWidth="1.5"
          strokeDasharray="2 3"
          className="text-slate-200"
        />
      </svg>
    );
  }
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const stepX = width / (data.length - 1);
  const pts = data.map((d, i) => {
    const x = i * stepX;
    const y = height - 3 - ((d - min) / range) * (height - 6);
    return [x, y] as const;
  });
  const line = pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const area = `${pts[0][0]},${height} ${line} ${pts[pts.length - 1][0]},${height}`;
  return (
    <svg width={width} height={height} className={className} aria-hidden="true">
      <polygon points={area} className="fill-emerald-500/10" />
      <polyline
        points={line}
        fill="none"
        className="stroke-emerald-500"
        strokeWidth="1.75"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <circle cx={pts[pts.length - 1][0]} cy={pts[pts.length - 1][1]} r="2" className="fill-emerald-500" />
    </svg>
  );
}

// --- Trend chip ------------------------------------------------------------
export function Trend({ delta }: { delta: number | null }) {
  if (delta === null || Number.isNaN(delta)) {
    return <span className="text-xs font-medium text-slate-300">—</span>;
  }
  const up = delta >= 0;
  return (
    <span
      className={cx(
        "inline-flex items-center gap-0.5 text-xs font-medium tabular-nums",
        up ? "text-emerald-600" : "text-rose-500",
      )}
    >
      <svg width="10" height="10" viewBox="0 0 12 12" fill="none" aria-hidden="true">
        <path
          d={up ? "M6 2.5v7M6 2.5 2.5 6M6 2.5 9.5 6" : "M6 9.5v-7M6 9.5 2.5 6M6 9.5 9.5 6"}
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      {Math.abs(delta)}%
    </span>
  );
}

export function trendFromSeries(series: number[]): number | null {
  if (!series || series.length < 2) return null;
  const last = series[series.length - 1];
  const prev = series[series.length - 2];
  if (prev === 0) return last === 0 ? 0 : 100;
  return Math.round(((last - prev) / prev) * 100);
}

// --- Card ------------------------------------------------------------------
export function Card({
  className,
  hover = false,
  children,
}: {
  className?: string;
  hover?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div
      className={cx(
        "rounded-xl border border-slate-200/70 bg-white shadow-card",
        hover &&
          "transition duration-200 ease-out hover:-translate-y-0.5 hover:shadow-card-md hover:border-slate-300/70",
        className,
      )}
    >
      {children}
    </div>
  );
}

// --- Skeleton --------------------------------------------------------------
export function Skeleton({ className }: { className?: string }) {
  return <div className={cx("skeleton", className)} />;
}

// --- PageHeader ------------------------------------------------------------
export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-[26px] font-semibold leading-tight text-slate-900">{title}</h1>
        {subtitle && <p className="mt-1.5 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {actions}
    </div>
  );
}

// --- Category badge --------------------------------------------------------
const CATEGORY_STYLES: Record<string, string> = {
  hot: "bg-emerald-600 text-white",
  warm: "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-600/20",
  cold: "bg-slate-100 text-slate-600",
  disqualified: "bg-slate-100 text-slate-400",
};

export function CategoryBadge({ category }: { category: string }) {
  return (
    <span
      className={cx(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize",
        CATEGORY_STYLES[category] ?? "bg-slate-100 text-slate-600",
      )}
    >
      {category}
    </span>
  );
}

// --- Score bar -------------------------------------------------------------
export function ScoreBar({ score }: { score: number }) {
  const pct = Math.max(0, Math.min(100, score));
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-emerald-500 transition-[width] duration-500 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-8 text-right text-sm font-semibold tabular-nums text-slate-900">
        {score.toFixed(0)}
      </span>
    </div>
  );
}

// --- Avatar ----------------------------------------------------------------
export function Avatar({ name }: { name: string }) {
  const initial = (name?.trim()?.[0] ?? "?").toUpperCase();
  return (
    <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-slate-100 text-sm font-semibold text-slate-500">
      {initial}
    </div>
  );
}

// --- Stat card -------------------------------------------------------------
export function StatCard({
  label,
  value,
  icon,
  series,
  accent,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
  series?: number[];
  accent?: boolean;
}) {
  return (
    <Card hover className="p-5">
      <div className="flex items-center justify-between">
        <span className="text-[13px] font-medium text-slate-500">{label}</span>
        <span
          className={cx(
            "flex h-8 w-8 items-center justify-center rounded-lg",
            accent ? "bg-emerald-50 text-emerald-600" : "bg-slate-50 text-slate-400",
          )}
        >
          {icon}
        </span>
      </div>
      <div className="mt-4 flex items-end justify-between">
        <div>
          <div className="text-[28px] font-semibold leading-none tracking-tight text-slate-900 tabular-nums">
            <Counter value={value} />
          </div>
          <div className="mt-2">
            <Trend delta={series ? trendFromSeries(series) : null} />
          </div>
        </div>
        <Sparkline data={series ?? []} />
      </div>
    </Card>
  );
}
