import type { Metadata } from "next";
import { Nav } from "@/components/Nav";
import { QueryProvider } from "@/lib/query-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "Adaptive Learning OS",
  description: "A personal Learning Operating System.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <QueryProvider>
          <Nav />
          <main className="mx-auto max-w-5xl px-6 py-8">{children}</main>
        </QueryProvider>
      </body>
    </html>
  );
}
