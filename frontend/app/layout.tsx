import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "RefundPilot AI",
  description:
    "A controlled AI customer-support agent for e-commerce refund decisions.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="font-sans min-h-screen">
        <header className="sticky top-0 z-30 glass">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-3">
            <Link href="/" className="flex items-center gap-3">
              <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 font-bold text-white shadow-lg shadow-indigo-500/30">
                R
              </span>
              <div className="leading-tight">
                <div className="text-sm font-semibold tracking-tight text-white">
                  RefundPilot <span className="text-indigo-400">AI</span>
                </div>
                <div className="text-[11px] text-slate-400">
                  Controlled refund decision agent
                </div>
              </div>
            </Link>
            <nav className="flex items-center gap-1 text-sm">
              {[
                { href: "/", label: "Customer Chat" },
                { href: "/policy", label: "Policy" },
                { href: "/crm", label: "CRM" },
                { href: "/admin", label: "Admin Logs" },
              ].map((l) => (
                <Link
                  key={l.href}
                  href={l.href}
                  className="rounded-lg px-3 py-1.5 text-slate-300 transition hover:bg-white/5 hover:text-white"
                >
                  {l.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-5 py-6">{children}</main>
      </body>
    </html>
  );
}
