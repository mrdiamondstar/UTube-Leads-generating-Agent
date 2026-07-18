"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useClickOutside } from "@/lib/useClickOutside";
import { fileToAvatarDataUrl } from "@/lib/image";
import { UserAvatar } from "@/components/UserAvatar";
import { cx } from "@/components/ui";
import { BellIcon, SettingsIcon } from "@/components/icons";

function IconButton({
  label,
  active,
  onClick,
  children,
}: {
  label: string;
  active?: boolean;
  onClick?: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      aria-label={label}
      className={cx(
        "focus-ring flex h-9 w-9 items-center justify-center rounded-lg transition",
        active ? "bg-slate-100 text-slate-700" : "text-slate-400 hover:bg-slate-100 hover:text-slate-700",
      )}
    >
      {children}
    </button>
  );
}

export function TopbarActions() {
  const { user, logout } = useAuth();
  const [menu, setMenu] = useState<null | "bell" | "user">(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const [limitReached, setLimitReached] = useState(false);
  const [leadsToday, setLeadsToday] = useState<number | null>(null);
  const [dailyLimit, setDailyLimit] = useState<number | null>(null);

  const bellRef = useRef<HTMLDivElement>(null);
  const userRef = useRef<HTMLDivElement>(null);
  useClickOutside(bellRef, () => setMenu(null), menu === "bell");
  useClickOutside(userRef, () => setMenu(null), menu === "user");

  // Poll the daily-lead status so the bell reflects "limit reached" without a
  // page reload. Light payload; every 60s and on focus.
  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    const load = () =>
      api
        .overview()
        .then((o) => {
          if (cancelled) return;
          setLimitReached(!!o.limit_reached);
          setLeadsToday(o.leads_today ?? null);
          setDailyLimit(o.daily_lead_limit ?? null);
        })
        .catch(() => {});
    load();
    const id = setInterval(load, 60_000);
    const onFocus = () => load();
    window.addEventListener("focus", onFocus);
    return () => {
      cancelled = true;
      clearInterval(id);
      window.removeEventListener("focus", onFocus);
    };
  }, [user]);

  if (!user) return null;

  const notifCount = limitReached ? 2 : 1;

  return (
    <div className="flex items-center gap-2">
      <span className="hidden rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[11px] font-medium text-emerald-700 lg:inline">
        Enterprise
      </span>

      {/* Notifications */}
      <div ref={bellRef} className="relative">
        <IconButton
          label="Notifications"
          active={menu === "bell"}
          onClick={() => setMenu(menu === "bell" ? null : "bell")}
        >
          <BellIcon className="h-[18px] w-[18px]" />
        </IconButton>
        <span className="pointer-events-none absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-rose-500 ring-2 ring-white" />
        {menu === "bell" && (
          <div className="absolute right-0 top-11 z-30 w-80 rounded-xl border border-slate-200/70 bg-white p-1.5 shadow-card-lg">
            <div className="flex items-center justify-between px-3 py-2">
              <span className="text-sm font-semibold text-slate-900">Notifications</span>
              <span className="rounded-full bg-emerald-50 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700">
                {notifCount} new
              </span>
            </div>
            <div className="space-y-1 px-1 pb-1">
              {limitReached && (
                <div className="rounded-lg bg-rose-50 px-3 py-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-rose-700">Today&apos;s limit reached</p>
                    <p className="mt-0.5 text-xs leading-relaxed text-rose-600/90">
                      You&apos;ve generated today&apos;s
                      {dailyLimit ? ` ${dailyLimit}` : " 500"}-lead limit
                      {leadsToday != null ? ` (${leadsToday} leads)` : ""}. New
                      discoveries will resume tomorrow.
                    </p>
                  </div>
                </div>
              )}
              <div className="rounded-lg bg-amber-50/70 px-3 py-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-slate-800">Data retention</p>
                  <p className="mt-0.5 text-xs leading-relaxed text-slate-500">
                    Your lead data will be retained for 30 days during your
                    subscription period. Please export your data before the
                    retention period ends. You&apos;ll receive a reminder 1 day
                    before your subscription expires.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Settings → profile editor */}
      <IconButton label="Settings" onClick={() => setProfileOpen(true)}>
        <SettingsIcon className="h-[18px] w-[18px]" />
      </IconButton>

      {/* User menu */}
      <div ref={userRef} className="relative ml-1">
        <button
          onClick={() => setMenu(menu === "user" ? null : "user")}
          aria-label="Account menu"
          className="focus-ring rounded-full"
        >
          <UserAvatar name={user.name} avatarUrl={user.avatar_url} size={32} />
        </button>
        {menu === "user" && (
          <div className="absolute right-0 top-11 z-30 w-64 rounded-xl border border-slate-200/70 bg-white p-1.5 shadow-card-lg">
            <div className="flex items-center gap-3 px-3 py-3">
              <UserAvatar name={user.name} avatarUrl={user.avatar_url} size={40} />
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold text-slate-900">{user.name}</div>
                <div className="truncate text-xs text-slate-500">{user.email}</div>
              </div>
            </div>
            <div className="my-1 border-t border-slate-100" />
            <MenuItem
              onClick={() => {
                setMenu(null);
                setProfileOpen(true);
              }}
            >
              Edit profile
            </MenuItem>
            <MenuItem danger onClick={logout}>
              Sign out
            </MenuItem>
          </div>
        )}
      </div>

      {profileOpen && <ProfileModal onClose={() => setProfileOpen(false)} />}
    </div>
  );
}

function MenuItem({
  children,
  onClick,
  danger,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  danger?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={cx(
        "focus-ring w-full rounded-lg px-3 py-2 text-left text-sm font-medium transition",
        danger ? "text-rose-600 hover:bg-rose-50" : "text-slate-600 hover:bg-slate-50",
      )}
    >
      {children}
    </button>
  );
}

function ProfileModal({ onClose }: { onClose: () => void }) {
  const { user, setUser } = useAuth();
  const [name, setName] = useState(user?.name ?? "");
  const [avatar, setAvatar] = useState<string | null>(user?.avatar_url ?? null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  if (!user) return null;

  const pickFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      setAvatar(await fileToAvatarDataUrl(file));
    } catch {
      setError("Could not load that image.");
    }
  };

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      const updated = await api.updateProfile({ name: name.trim(), avatar_url: avatar });
      setUser(updated);
      onClose();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-2xl bg-white p-6 shadow-card-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-semibold text-slate-900">Edit profile</h3>
        <p className="mt-0.5 text-sm text-slate-500">Update your name and photo.</p>

        <div className="mt-5 flex items-center gap-4">
          <UserAvatar name={name || user.name} avatarUrl={avatar} size={64} />
          <div className="flex flex-col gap-2">
            <button
              onClick={() => fileRef.current?.click()}
              className="focus-ring rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
            >
              Upload photo
            </button>
            {avatar && (
              <button
                onClick={() => setAvatar(null)}
                className="text-left text-xs font-medium text-slate-400 hover:text-rose-600"
              >
                Remove photo
              </button>
            )}
            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              onChange={pickFile}
              className="hidden"
            />
          </div>
        </div>

        <label className="mt-5 block">
          <span className="mb-1.5 block text-sm font-medium text-slate-700">Full name</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="focus-ring w-full rounded-lg border border-slate-200 bg-slate-50/60 px-3 py-2 text-sm text-slate-900 focus:border-emerald-500 focus:bg-white"
          />
        </label>

        <div className="mt-5 flex items-center gap-3 rounded-lg bg-slate-50 px-3 py-2">
          <span className="text-xs text-slate-400">Email</span>
          <span className="text-sm text-slate-600">{user.email}</span>
        </div>

        {error && <p className="mt-3 text-sm text-rose-600">{error}</p>}

        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="focus-ring rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
          >
            Cancel
          </button>
          <button
            onClick={save}
            disabled={busy || !name.trim()}
            className="focus-ring rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-700 disabled:opacity-50"
          >
            {busy ? "Saving…" : "Save changes"}
          </button>
        </div>
      </div>
    </div>
  );
}
