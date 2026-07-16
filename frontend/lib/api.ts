// Resolve the backend base URL.
// 1. If NEXT_PUBLIC_API_BASE_URL is set at build time, always use it.
// 2. Otherwise, use localhost only when actually running on localhost (dev).
// 3. In any deployed environment, fall back to the live Render backend so the
//    app works even if the env var wasn't configured in the host.
function resolveApiBase(): string {
  const fromEnv = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (fromEnv && fromEnv.length > 0) return fromEnv;
  if (
    typeof window !== "undefined" &&
    (window.location.hostname === "localhost" ||
      window.location.hostname === "127.0.0.1")
  ) {
    return "http://localhost:8000";
  }
  return "https://utube-leads-generating-agent.onrender.com";
}

export const API_BASE = resolveApiBase();

export interface RunPoint {
  discovered: number;
  qualified: number;
  underperforming: number;
  hot: number;
}

export interface Overview {
  total_channels: number;
  total_scored: number;
  underperforming: number;
  by_category: Record<string, number>;
  recent_runs: RunPoint[];
}

export interface Channel {
  id: string;
  youtube_id: string;
  title: string;
  country: string | null;
  country_name: string | null;
  youtube_url: string;
  category: string | null;
  subscriber_count: number;
  view_count: number;
  video_count: number;
  website: string | null;
  public_email: string | null;
  social_links: Record<string, string>;
}

export interface Video {
  id: string;
  channel_id: string;
  youtube_video_id: string;
  youtube_url: string;
  title: string;
  published_at: string | null;
  view_count: number;
  like_count: number;
  comment_count: number;
}

export interface LeadScore {
  id: string;
  channel_id: string;
  score: number;
  confidence: number;
  category: "hot" | "warm" | "cold" | "disqualified";
  is_underperforming: boolean;
  feature_contributions: Record<
    string,
    { strength: number; weight: number; contribution: number }
  >;
  reasoning: string;
  created_at: string;
}

export type LeadStatus = "active" | "interested" | "closed" | "rejected";
export const LEAD_STATUSES: LeadStatus[] = [
  "active",
  "interested",
  "closed",
  "rejected",
];

export interface Lead {
  channel: Channel;
  score: LeadScore;
  latest_video: Video | null;
  niche: string | null;
  status: LeadStatus;
}

export interface LeadDetail {
  channel: Channel;
  score: LeadScore | null;
  videos: Video[];
}

// ---- auth token handling --------------------------------------------------
const TOKEN_KEY = "cip_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

function authHeaders(): Record<string, string> {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}

// ---- last discovery (drives the "show only the current search" leads view) --
// We remember the exact pipeline run IDs of the most recent discovery so the
// Leads page shows ONLY those results — never anything from previous searches,
// even for the same niche. `niches` is kept only for a friendly display label.
const LAST_DISCOVERY_KEY = "cip_last_discovery";

export interface LastDiscovery {
  runIds: string[];
  niches: string[];
}

export function setLastDiscovery(runIds: string[], niches: string[]): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(
    LAST_DISCOVERY_KEY,
    JSON.stringify({ runIds, niches } satisfies LastDiscovery),
  );
}

export function getLastDiscovery(): LastDiscovery {
  if (typeof window === "undefined") return { runIds: [], niches: [] };
  try {
    const raw = localStorage.getItem(LAST_DISCOVERY_KEY);
    const parsed = raw ? JSON.parse(raw) : {};
    const runIds = Array.isArray(parsed.runIds)
      ? parsed.runIds.filter((x: unknown) => typeof x === "string")
      : [];
    const niches = Array.isArray(parsed.niches)
      ? parsed.niches.filter((x: unknown) => typeof x === "string")
      : [];
    return { runIds, niches };
  } catch {
    return { runIds: [], niches: [] };
  }
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error(`API ${path} -> ${res.status}`);
  return res.json();
}

export interface User {
  id: string;
  email: string;
  name: string;
  avatar_url: string | null;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

async function authPost(path: string, body: unknown): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
  return data as AuthResponse;
}

export interface Plan {
  id: string;
  name: string;
  interval: string;
  period_days: number;
  amount_cents: number;
  amount: number;
  per_day_cents: number;
  currency: string;
  tagline: string;
  features: string[];
  highlight: boolean;
  badge: string | null;
}

export interface Subscription {
  id: string;
  customer_email: string;
  plan_id: string;
  interval: string;
  amount_cents: number;
  currency: string;
  status: string;
  started_at: string;
  current_period_end: string;
}

export interface BillingConfig {
  enabled: boolean;
  provider: string;
  key_id: string | null;
  currency: string;
}

export interface Checkout {
  order_id: string;
  amount: number;
  currency: string;
  key_id: string;
  plan_id: string;
  plan_name: string;
  email: string;
}

export interface VerifyPaymentPayload {
  plan_id: string;
  email: string;
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}

async function jsonPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((data as { detail?: string }).detail || `Request failed (${res.status})`);
  return data as T;
}

export interface Niche {
  id: string;
  name: string;
  category: string;
  popularity: number;
  recommended: boolean;
  language: string;
  created_at: string;
}

// Build the query string for the leads list/export endpoints so both share the
// exact same category + run-id filtering.
export function leadsQuery(category?: string, runIds?: string[]): string {
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  (runIds ?? []).forEach((id) => params.append("run_id", id));
  const s = params.toString();
  return s ? `?${s}` : "";
}

export const api = {
  overview: () => get<Overview>("/api/v1/overview"),
  niches: () => get<Niche[]>("/api/v1/niches"),
  leads: (
    category?: string,
    runIds?: string[],
    status?: string,
    underperforming?: boolean,
  ) =>
    get<Lead[]>(
      `/api/v1/leads?limit=100${leadsQuery(category, runIds).replace("?", "&")}${
        status ? `&status=${status}` : ""
      }${underperforming ? "&underperforming=1" : ""}`,
    ),
  setLeadStatus: async (
    channelId: string,
    status: LeadStatus,
  ): Promise<{ channel_id: string; status: LeadStatus }> => {
    const res = await fetch(`${API_BASE}/api/v1/leads/${channelId}/status`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ status }),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body.detail || `Update failed (${res.status})`);
    return body;
  },
  leadDetail: (id: string) => get<LeadDetail>(`/api/v1/leads/${id}/detail`),
  runPipeline: async (
    query: string,
    max_results = 25,
    force = false,
  ): Promise<{ id: string; reused: boolean }> => {
    const res = await fetch(`${API_BASE}/api/v1/pipeline/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, max_results, force }),
    });
    if (!res.ok) throw new Error(`run failed: ${res.status}`);
    return res.json();
  },
  register: (name: string, email: string, password: string) =>
    authPost("/api/v1/auth/register", { name, email, password }),
  login: (email: string, password: string) =>
    authPost("/api/v1/auth/login", { email, password }),
  me: () => get<User>("/api/v1/auth/me"),
  updateProfile: async (data: { name?: string; avatar_url?: string | null }): Promise<User> => {
    const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(data),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body.detail || `Update failed (${res.status})`);
    return body as User;
  },
  plans: () => get<Plan[]>("/api/v1/billing/plans"),
  billingConfig: () => get<BillingConfig>("/api/v1/billing/config"),
  subscribe: (plan_id: string, email: string) =>
    jsonPost<Subscription>("/api/v1/billing/subscribe", { plan_id, email }),
  createCheckout: (plan_id: string, email: string) =>
    jsonPost<Checkout>("/api/v1/billing/checkout", { plan_id, email }),
  verifyPayment: (payload: VerifyPaymentPayload) =>
    jsonPost<Subscription>("/api/v1/billing/verify", payload),
};
