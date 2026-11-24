import type { Metadata } from "next";
import Link from "next/link";
import "@xyflow/react/dist/style.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "AIIREP | Engineering Digital Twin",
  description: "Industrial reverse engineering and validated digital twin workspace",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <aside className="sidebar">
            <Link className="brand" href="/">
              <span className="brand-mark">A</span>
              <span>AIIREP<small>ENGINEERING INTELLIGENCE</small></span>
            </Link>
            <div className="nav-label">WORKSPACE</div>
            <nav>
              <Link href="/">Overview</Link>
              <Link href="/engineering-review">Engineering review</Link>
              <Link href="/library">Production library</Link>
            </nav>
            <div className="sidebar-bottom">
              <span className="online-dot" /> Local development environment
            </div>
          </aside>
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}
