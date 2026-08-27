import Link from "next/link";

const LINKS = [
  { href: "/", label: "Home" },
  { href: "/library", label: "Library" },
  { href: "/search", label: "Search" },
  { href: "/subjects", label: "Subjects" },
];

export function Nav() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-5xl items-center gap-6 px-6 py-4">
        <Link href="/" className="font-semibold text-slate-900">
          Adaptive Learning OS
        </Link>
        <nav className="flex gap-4 text-sm text-slate-600">
          {LINKS.map((link) => (
            <Link key={link.href} href={link.href} className="hover:text-brand-600">
              {link.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
