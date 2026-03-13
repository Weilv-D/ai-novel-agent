import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI Novel Agent",
  description: "AI-powered long-form novel writing system",
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
