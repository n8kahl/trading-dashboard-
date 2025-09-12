import type { Metadata } from "next";
import "./globals.css";
import QueryProvider from "./(providers)/query";

export const metadata: Metadata = {
  title: "Trading Assistant Dashboard",
  description: "Control panel for the Trading Assistant API",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
