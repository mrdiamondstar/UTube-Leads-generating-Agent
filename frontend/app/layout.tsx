import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AppShell } from "@/components/AppShell";
import { AuthProvider } from "@/lib/auth";
import { ToastProvider } from "@/lib/toast";
import { DiscoveryProvider } from "@/components/DiscoveryProvider";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Creator Intelligence Platform",
  description: "Discover, analyze, and score YouTube creator leads.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body>
        <AuthProvider>
          <ToastProvider>
            <DiscoveryProvider>
              <AppShell>{children}</AppShell>
            </DiscoveryProvider>
          </ToastProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
