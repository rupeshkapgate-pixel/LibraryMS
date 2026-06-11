"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, BookOpen, Users, BookMarked,
  AlertTriangle, ArrowLeftRight, RotateCcw, Menu, X,
} from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

const nav = [
  { label: "Dashboard",       href: "/",                icon: LayoutDashboard },
  { label: "Books",           href: "/books",           icon: BookOpen },
  { label: "Members",         href: "/members",         icon: Users },
  { label: "Borrow Book",     href: "/lending/borrow",  icon: ArrowLeftRight },
  { label: "Return Book",     href: "/lending/return",  icon: RotateCcw },
  { label: "Borrowed Books",  href: "/lending/borrowed",icon: BookMarked },
  { label: "Overdue Books",   href: "/lending/overdue", icon: AlertTriangle },
];

function isActivePath(path: string, href: string) {
  if (href === "/") {
    return path === "/";
  }

  // Books and members have nested detail/edit pages, so their parent menu item
  // should remain active for child routes.
  if (href === "/books" || href === "/members") {
    return path === href || path.startsWith(`${href}/`);
  }

  // Lending routes share prefixes, for example /lending/borrow and
  // /lending/borrowed. Use exact matching to avoid highlighting both.
  return path === href;
}

export default function Sidebar() {
  const path = usePathname();
  const [open, setOpen] = useState(false);

  const links = (
    <ul className="space-y-0.5">
      {nav.map(({ label, href, icon: Icon }) => {
        const active = isActivePath(path, href);
        return (
          <li key={href}>
            <Link
              href={href}
              onClick={() => setOpen(false)}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                active
                  ? "bg-brand-600 text-white"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              )}
            >
              <Icon size={18} />
              {label}
            </Link>
          </li>
        );
      })}
    </ul>
  );

  return (
    <>
      {/* Mobile toggle */}
      <button
        onClick={() => setOpen(true)}
        className="lg:hidden fixed top-4 left-4 z-40 p-2 bg-white rounded-lg shadow border border-gray-200"
      >
        <Menu size={20} />
      </button>

      {/* Mobile overlay */}
      {open && (
        <div
          className="lg:hidden fixed inset-0 z-40 bg-black/30"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed top-0 left-0 z-50 h-full w-64 bg-white border-r border-gray-200 flex flex-col transition-transform duration-200",
          "lg:translate-x-0 lg:static lg:z-auto",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex items-center justify-between h-16 px-5 border-b border-gray-200">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center">
              <BookOpen size={18} className="text-white" />
            </div>
            <span className="font-bold text-gray-900">LibraryMS</span>
          </div>
          <button onClick={() => setOpen(false)} className="lg:hidden p-1 text-gray-400 hover:text-gray-600">
            <X size={18} />
          </button>
        </div>
        <nav className="flex-1 overflow-y-auto p-4">{links}</nav>
        <div className="p-4 border-t border-gray-200">
          <p className="text-xs text-gray-400 text-center">Library Management System v1.0</p>
        </div>
      </aside>
    </>
  );
}
