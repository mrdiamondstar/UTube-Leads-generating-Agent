"use client";

import { useEffect, useState } from "react";
import { api, BillingConfig, Plan, Subscription } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { UPI_WITH_MANUAL_ID, loadRazorpay } from "@/lib/razorpay";

function formatMoney(paise: number): string {
  const rupees = paise / 100;
  // Indian digit grouping (₹1,00,000). Drop decimals for whole amounts.
  return (
    "₹" +
    rupees.toLocaleString("en-IN", {
      minimumFractionDigits: Number.isInteger(rupees) ? 0 : 2,
      maximumFractionDigits: 2,
    })
  );
}

function intervalLabel(interval: string): string {
  return { day: "/day", week: "/week", month: "/month" }[interval] ?? "";
}

export default function PricingPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [config, setConfig] = useState<BillingConfig | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Plan | null>(null);

  useEffect(() => {
    api.plans().then(setPlans).catch((e) => setError((e as Error).message));
    api.billingConfig().then(setConfig).catch(() => setConfig(null));
  }, []);

  const dailyPerDay = plans.find((p) => p.id === "daily")?.per_day_cents ?? null;

  return (
    <div className="mx-auto max-w-5xl">
      {/* Header */}
      <div className="mx-auto max-w-2xl text-center">
        <span className="inline-block rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
          Subscription
        </span>
        <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
          Simple, transparent pricing
        </h1>
        <p className="mt-3 text-slate-500">
          Choose the access that fits your workflow. Upgrade, downgrade, or cancel
          anytime — no long-term contract.
        </p>
      </div>

      {error && (
        <p className="mt-8 text-center text-sm text-red-600">
          Couldn&apos;t load plans: {error}
        </p>
      )}

      {/* Plan grid */}
      <div className="mt-12 grid items-start gap-6 md:grid-cols-3">
        {plans.map((plan) => {
          const savings =
            dailyPerDay && plan.id !== "daily"
              ? Math.round((1 - plan.per_day_cents / dailyPerDay) * 100)
              : 0;
          return (
            <div
              key={plan.id}
              className={[
                "relative flex h-full flex-col rounded-2xl bg-white p-8 transition",
                plan.highlight
                  ? "border-2 border-emerald-600 shadow-xl md:-mt-4"
                  : "border border-slate-200 shadow-sm",
              ].join(" ")}
            >
              {plan.badge && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-emerald-600 px-3 py-1 text-xs font-semibold text-white shadow">
                  {plan.badge}
                </span>
              )}

              <h2 className="text-lg font-semibold text-slate-900">{plan.name}</h2>
              <p className="mt-1 text-sm text-slate-500">{plan.tagline}</p>

              <div className="mt-6 flex items-baseline gap-1">
                <span className="text-4xl font-semibold tracking-tight text-slate-900">
                  {formatMoney(plan.amount_cents)}
                </span>
                <span className="text-sm font-medium text-slate-400">
                  {intervalLabel(plan.interval)}
                </span>
              </div>
              <div className="mt-1 flex items-center gap-2 text-xs text-slate-400">
                <span>≈ {formatMoney(plan.per_day_cents)}/day</span>
                {savings > 0 && (
                  <span className="rounded-full bg-emerald-50 px-2 py-0.5 font-medium text-emerald-700">
                    Save {savings}%
                  </span>
                )}
              </div>

              <button
                onClick={() => setSelected(plan)}
                className={[
                  "mt-6 w-full rounded-lg px-4 py-2.5 text-sm font-medium transition",
                  plan.highlight
                    ? "bg-emerald-600 text-white hover:bg-emerald-700"
                    : "border border-slate-300 text-slate-800 hover:bg-slate-50",
                ].join(" ")}
              >
                Choose {plan.name}
              </button>

              <ul className="mt-8 space-y-3 border-t border-slate-100 pt-6">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2.5 text-sm text-slate-600">
                    <CheckIcon />
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>

      <p className="mt-10 text-center text-xs text-slate-400">
        Prices in INR. Taxes may apply.{" "}
        {config?.enabled
          ? "Payments are securely processed by Razorpay."
          : "Demo mode — checkout is simulated until payment keys are configured."}
      </p>

      {selected && (
        <SubscribeDialog
          plan={selected}
          enabled={!!config?.enabled}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}

function CheckIcon() {
  return (
    <svg
      className="mt-0.5 h-4 w-4 flex-shrink-0 text-emerald-600"
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function SubscribeDialog({
  plan,
  enabled,
  onClose,
}: {
  plan: Plan;
  enabled: boolean;
  onClose: () => void;
}) {
  const { user } = useAuth();
  const email = user?.email ?? "";
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<Subscription | null>(null);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      if (enabled) {
        const loaded = await loadRazorpay();
        if (!loaded) throw new Error("Could not load the payment gateway.");
        const co = await api.createCheckout(plan.id, email.trim());
        const rzp = new window.Razorpay!({
          key: co.key_id,
          order_id: co.order_id,
          amount: co.amount,
          currency: co.currency,
          name: "Creator Intelligence Platform",
          description: `${plan.name} plan`,
          prefill: { email: co.email, name: user?.name },
          theme: { color: "#059669" },
          config: UPI_WITH_MANUAL_ID,
          handler: async (resp) => {
            try {
              setDone(
                await api.verifyPayment({
                  plan_id: plan.id,
                  email: email.trim(),
                  razorpay_order_id: resp.razorpay_order_id,
                  razorpay_payment_id: resp.razorpay_payment_id,
                  razorpay_signature: resp.razorpay_signature,
                }),
              );
            } catch (e) {
              setError((e as Error).message);
            } finally {
              setBusy(false);
            }
          },
          modal: { ondismiss: () => setBusy(false) },
        });
        rzp.open();
        return; // busy stays until the Razorpay handler/dismiss fires
      }
      setDone(await api.subscribe(plan.id, email.trim()));
      setBusy(false);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {!done ? (
          <>
            <h3 className="text-lg font-semibold text-slate-900">
              Subscribe to {plan.name}
            </h3>
            <p className="mt-1 text-sm text-slate-500">
              {formatMoney(plan.amount_cents)}
              {intervalLabel(plan.interval)} · billed each {plan.interval}.
            </p>

            <div className="mt-5 flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5">
              <span className="text-xs text-slate-400">Billing account</span>
              <span className="text-sm font-medium text-slate-700">{email}</span>
            </div>

            {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

            <div className="mt-6 flex items-center justify-between gap-3">
              <span className="text-xs text-slate-400">
                {enabled ? "🔒 Secured by Razorpay" : "Demo · no card charged"}
              </span>
              <div className="flex gap-3">
                <button
                  onClick={onClose}
                  className="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  onClick={submit}
                  disabled={busy || !email}
                  className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                >
                  {busy ? "Processing…" : enabled ? "Continue to payment" : "Confirm subscription"}
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="text-center">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100">
              <CheckIcon />
            </div>
            <h3 className="mt-4 text-lg font-semibold text-slate-900">
              You&apos;re subscribed 🎉
            </h3>
            <p className="mt-1 text-sm text-slate-500">
              {plan.name} plan is active for {done.customer_email}.
            </p>
            <p className="mt-1 text-sm text-slate-500">
              Renews on{" "}
              <span className="font-medium text-slate-700">
                {new Date(done.current_period_end).toLocaleDateString()}
              </span>
              .
            </p>
            <button
              onClick={onClose}
              className="mt-6 w-full rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-800"
            >
              Done
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
