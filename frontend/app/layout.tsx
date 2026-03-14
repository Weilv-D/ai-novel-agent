import type { Metadata } from "next";
import { Cormorant_Garamond, Noto_Serif_SC } from "next/font/google";

const bodyFont = Noto_Serif_SC({
  variable: "--font-serif",
  weight: ["400", "500", "600", "700"],
  subsets: ["latin"],
  display: "swap",
});

const displayFont = Cormorant_Garamond({
  variable: "--font-display",
  weight: ["400", "500", "600", "700"],
  subsets: ["latin"],
  display: "swap",
});

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
    <html lang="zh-CN" className={`${bodyFont.variable} ${displayFont.variable}`}>
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
