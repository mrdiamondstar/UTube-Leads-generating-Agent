/** Razorpay Checkout — dynamic script loader + minimal types. */

export interface RazorpaySuccess {
  razorpay_payment_id: string;
  razorpay_order_id: string;
  razorpay_signature: string;
}

export interface RazorpayOptions {
  key: string;
  order_id: string;
  amount: number;
  currency: string;
  name: string;
  description?: string;
  prefill?: { email?: string; name?: string; contact?: string };
  theme?: { color?: string };
  handler: (response: RazorpaySuccess) => void;
  modal?: { ondismiss?: () => void };
  // Custom method/flow display (e.g. force the "Enter UPI ID" collect flow).
  config?: {
    display?: {
      blocks?: Record<
        string,
        { name: string; instruments: { method: string; flows?: string[] }[] }
      >;
      sequence?: string[];
      preferences?: { show_default_blocks?: boolean };
    };
  };
}

/** A UPI block that shows QR, intent AND the manual "Enter UPI ID" (collect) flow. */
export const UPI_WITH_MANUAL_ID: NonNullable<RazorpayOptions["config"]> = {
  display: {
    blocks: {
      upi: {
        name: "Pay using UPI",
        instruments: [{ method: "upi", flows: ["collect", "qr", "intent"] }],
      },
    },
    sequence: ["block.upi"],
    preferences: { show_default_blocks: true },
  },
};

interface RazorpayInstance {
  open: () => void;
}

declare global {
  interface Window {
    Razorpay?: new (options: RazorpayOptions) => RazorpayInstance;
  }
}

const SCRIPT_SRC = "https://checkout.razorpay.com/v1/checkout.js";

export function loadRazorpay(): Promise<boolean> {
  return new Promise((resolve) => {
    if (typeof window === "undefined") return resolve(false);
    if (window.Razorpay) return resolve(true);
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${SCRIPT_SRC}"]`);
    if (existing) {
      existing.addEventListener("load", () => resolve(true));
      existing.addEventListener("error", () => resolve(false));
      return;
    }
    const script = document.createElement("script");
    script.src = SCRIPT_SRC;
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}
