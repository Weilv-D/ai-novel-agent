import "./globals.css";

import type { Metadata } from "next";

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
        {children}
      </body>
    </html>
  );
}
