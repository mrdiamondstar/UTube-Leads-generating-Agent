export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

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

export interface Lead {
  channel: Channel;
  score: LeadScore;
  latest_video: Video | null;
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

export const api = {
  overview: () => get<Overview>("/api/v1/overview"),
  niches: () => get<Niche[]>("/api/v1/niches"),
  leads: (category?: string) =>
    get<Lead[]>(`/api/v1/leads?limit=100${category ? `&category=${category}` : ""}`),
  leadDetail: (id: string) => get<LeadDetail>(`/api/v1/leads/${id}/detail`),
  runPipeline: async (query: string, max_results = 25) => {
    const res = await fetch(`${API_BASE}/api/v1/pipeline/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, max_results }),
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
