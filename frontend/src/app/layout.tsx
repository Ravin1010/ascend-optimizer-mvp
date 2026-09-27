import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Ascend Optimizer",
  description: "Live 0G strategy and yield optimizer",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
