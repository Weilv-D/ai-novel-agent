import "./globals.css";

import type { Metadata } from "next";
import { ToastProvider } from "@/components/ui/Toast";
import { PreferencesInit } from "@/components/PreferencesInit";
import { GlobalProgressBar } from "@/components/GlobalProgressBar";
import { MobileNav } from "@/components/MobileNav";
import { NetworkStatusIndicator } from "@/components/NetworkStatusIndicator";

export const metadata: Metadata = {
  title: "AI Novel Agent",
  description: "AI-powered novel workspace with an ink-wash creative interface",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="antialiased">
        <PreferencesInit />
        <GlobalProgressBar />
        <NetworkStatusIndicator />
        <ToastProvider>
          {children}
        </ToastProvider>
        <MobileNav />
      </body>
    </html>
  );
}
