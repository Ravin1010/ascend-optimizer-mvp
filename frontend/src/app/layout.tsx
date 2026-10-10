import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Ascend Optimizer",
  description: "Decision-sleeve optimizer prototype with explicit evidence qualification",
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
