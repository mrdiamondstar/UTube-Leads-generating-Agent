"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import React, { useEffect, useState } from "react";
import { cx } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { TopbarActions } from "@/components/TopbarActions";
import { GridIcon, MenuIcon, TagIcon, UsersIcon, XIcon } from "@/components/icons";

const NAV = [
  { href: "/", label: "Overview", icon: GridIcon },
  { href: "/leads", label: "Leads", icon: UsersIcon },
  { href: "/pricing", label: "Subscription", icon: TagIcon },
];

function titleFor(pathname: string): string {
  if (pathname.startsWith("/leads")) return "Leads";
  return NAV.find((n) => n.href === pathname)?.label ?? "Overview";
}

function Brand() {
  return (
    <div className="flex items-center gap-2.5">
      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500 text-sm font-bold text-white shadow-sm">
        C
      </div>
      <div className="leading-tight">
        <div className="text-[13px] font-semibold text-white">Creator Intelligence</div>
        <div className="text-[11px] text-slate-500">Platform</div>
      </div>
    </div>
  );
}

function NavLinks({
  pathname,
  onNavigate,
}: {
  pathname: string;
  onNavigate: () => void;
}) {
  return (
    <>
      {NAV.map(({ href, label, icon: Icon }) => {
        const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={cx(
              "focus-ring group relative flex items-center gap-3 rounded-lg px-3 py-2 text-[13px] font-medium transition duration-150 ease-out",
              active
                ? "bg-emerald-500/10 text-emerald-400"
                : "text-slate-400 hover:bg-white/5 hover:text-slate-100",
            )}
          >
            {active && (
              <span className="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-emerald-400" />
            )}
            <Icon className="h-[18px] w-[18px]" />
            {label}
          </Link>
        );
      })}
    </>
  );
}

function FullscreenLoader() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50">
      <svg className="h-6 w-6 animate-spin text-emerald-600" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
        <path className="opacity-90" fill="currentColor" d="M4 12a8 8 0 0 1 8-8v3a5 5 0 0 0-5 5H4z" />
      </svg>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading } = useAuth();
  const [navOpen, setNavOpen] = useState(false);

  const isLogin = pathname === "/login";

  useEffect(() => {
    if (!loading && !user && !isLogin) router.replace("/login");
  }, [loading, user, isLogin, router]);

  // Close the drawer when the route changes.
  useEffect(() => {
    setNavOpen(false);
  }, [pathname]);

  // Escape closes the drawer.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setNavOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const focusSearch = () => {
    const el = document.getElementById("discovery-input");
    if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  if (isLogin) return <>{children}</>;
  if (loading || !user) return <FullscreenLoader />;

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Backdrop */}
      <div
        onClick={() => setNavOpen(false)}
        aria-hidden="true"
        className={cx(
          "fixed inset-0 z-30 bg-slate-900/40 transition-opacity duration-200",
          navOpen ? "opacity-100" : "pointer-events-none opacity-0",
        )}
      />

      {/* Slide-in navigation drawer */}
      <aside
        aria-hidden={!navOpen}
        className={cx(
          "fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-slate-900 shadow-2xl transition-transform duration-200 ease-out",
          navOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex items-center justify-between px-4 py-4">
          <Brand />
          <button
            onClick={() => setNavOpen(false)}
            aria-label="Close navigation"
            className="focus-ring flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition hover:bg-white/5 hover:text-white"
          >
            <XIcon className="h-4 w-4" />
          </button>
        </div>
        <div className="mx-3 mb-2 border-t border-slate-800" />
        <nav className="flex flex-1 flex-col gap-0.5 px-3">
          <p className="px-3 pb-1.5 pt-2 text-[11px] font-medium uppercase tracking-wider text-slate-600">
            Workspace
          </p>
          <NavLinks pathname={pathname} onNavigate={() => setNavOpen(false)} />
        </nav>
        <div className="p-3">
          <div className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-800/40 px-3 py-2.5">
            <span className="relative flex h-2 w-2">
              <span className="pulse-dot absolute inline-flex h-2 w-2 rounded-full bg-emerald-400" />
              <span className="inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            </span>
            <span className="text-xs text-slate-400">Live · YouTube API</span>
          </div>
        </div>
      </aside>

      {/* Top bar (full width) */}
      <header className="sticky top-0 z-20 flex items-center justify-between border-b border-slate-200/80 bg-white/70 px-4 py-2.5 backdrop-blur-md sm:px-6">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setNavOpen(true)}
            aria-label="Open navigation"
            aria-expanded={navOpen}
            className="focus-ring flex h-9 w-9 items-center justify-center rounded-lg text-slate-500 transition hover:bg-slate-100 hover:text-slate-700"
          >
            <MenuIcon className="h-5 w-5" />
          </button>
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-500 text-xs font-bold text-white">
              C
            </div>
            <span className="text-sm font-medium text-slate-900">{titleFor(pathname)}</span>
          </div>
          <a
            href="https://www.youtube.com"
            target="_blank"
            rel="noreferrer"
            title="Creator data is sourced from YouTube via the YouTube Data API"
            className="focus-ring hidden items-center gap-1.5 rounded-full border border-slate-200 px-2.5 py-1 text-[11px] font-medium text-slate-500 transition hover:border-slate-300 hover:text-slate-700 sm:inline-flex"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-red-500" aria-hidden="true" />
            Data from YouTube
          </a>
        </div>
        <TopbarActions onFocusSearch={focusSearch} />
      </header>

      <main className="p-5 sm:p-8">
        <div className="mx-auto max-w-6xl">{children}</div>
        {/* YouTube API Terms: attribution + derived-metrics disclosure. */}
        <footer className="mx-auto mt-10 max-w-6xl border-t border-slate-200 pt-4 text-xs leading-relaxed text-slate-400">
          Creator data is sourced from{" "}
          <a
            href="https://www.youtube.com"
            target="_blank"
            rel="noreferrer"
            className="font-medium text-slate-500 hover:text-emerald-700"
          >
            YouTube
          </a>{" "}
          via the YouTube Data API. Lead scores and opportunity match tiers
          (Excellent / Strong / Moderate / Low Match) are Creator Intelligence
          Platform&apos;s own analysis — <span className="font-medium">not YouTube metrics</span>.
          Subscriber, view, and video counts are shown as reported by YouTube.
        </footer>
      </main>
    </div>
  );
}
