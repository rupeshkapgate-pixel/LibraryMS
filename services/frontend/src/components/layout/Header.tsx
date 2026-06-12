"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  Bell,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  Command,
  LayoutDashboard,
  Moon,
  PlusCircle,
  RotateCcw,
  Search,
  Settings,
  Sun,
  UserCircle,
  Users,
  X,
} from "lucide-react";
import { API_BASE } from "@/lib/api";
import { cn } from "@/lib/utils";

type Theme = "light" | "dark" | "system";

const commands = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "Books", href: "/books", icon: BookOpen },
  { label: "Add Book", href: "/books/add", icon: PlusCircle },
  { label: "Members", href: "/members", icon: Users },
  { label: "Add Member", href: "/members/add", icon: PlusCircle },
  { label: "Borrow Book", href: "/lending/borrow", icon: Command },
  { label: "Return Book", href: "/lending/return", icon: RotateCcw },
];

const notifications = [
  { title: "Catalogue healthy", message: "Books API is responding normally.", tone: "green" },
  { title: "Low stock watch", message: "Review books with 1–2 available copies.", tone: "amber" },
  { title: "Overdue queue", message: "Check overdue books before daily close.", tone: "red" },
];

function applyTheme(theme: Theme) {
  const isDark = theme === "dark" || (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", isDark);
}

export default function Header() {
  const router = useRouter();
  const pathname = usePathname();
  const [theme, setTheme] = useState<Theme>("light");
  const [themeOpen, setThemeOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [cmdOpen, setCmdOpen] = useState(false);
  const [query, setQuery] = useState("");

  useEffect(() => {
    const saved = (localStorage.getItem("lms-theme") as Theme | null) ?? "light";
    setTheme(saved);
    applyTheme(saved);
  }, []);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCmdOpen(true);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const setSelectedTheme = (next: Theme) => {
    setTheme(next);
    localStorage.setItem("lms-theme", next);
    applyTheme(next);
    setThemeOpen(false);
  };

  const filteredCommands = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q ? commands.filter((c) => c.label.toLowerCase().includes(q)) : commands;
  }, [query]);

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/90 shadow-sm backdrop-blur dark:border-slate-800 dark:bg-slate-950/80">
      <div className="flex h-16 items-center justify-end gap-3 px-4 sm:px-6 lg:px-8">
        <button
          onClick={() => setCmdOpen(true)}
          className="hidden items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50/80 px-3 py-2 text-sm font-medium text-slate-500 transition hover:border-indigo-200 hover:bg-white hover:text-slate-800 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400 dark:hover:bg-slate-900/70 md:flex"
          type="button"
        >
          <Search size={16} />
          <span>Command menu</span>
          <kbd className="rounded-md border border-slate-200 bg-white px-1.5 py-0.5 text-[10px] dark:border-slate-700 dark:bg-slate-800">Ctrl K</kbd>
        </button>
        <span className="hidden rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 ring-1 ring-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-300 dark:ring-emerald-500/20 sm:inline">
          API: {API_BASE.replace(/^https?:\/\//, "")}
        </span>

        <div className="relative">
          <button onClick={() => setThemeOpen((v) => !v)} className="rounded-xl border border-slate-200 bg-white p-2 text-slate-500 shadow-sm transition hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300" aria-label="Theme" type="button">
            {theme === "dark" ? <Moon size={18} /> : <Sun size={18} />}
          </button>
          {themeOpen && (
            <div className="absolute right-0 mt-2 w-44 rounded-2xl border border-slate-200 bg-white p-2 shadow-xl dark:border-slate-800 dark:bg-slate-900">
              {(["light", "dark", "system"] as Theme[]).map((item) => (
                <button key={item} onClick={() => setSelectedTheme(item)} className={cn("flex w-full items-center justify-between rounded-xl px-3 py-2 text-sm capitalize text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800", theme === item && "bg-indigo-50 font-semibold text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300")} type="button">
                  {item}
                  {theme === item && <CheckCircle2 size={15} />}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="relative">
          <button onClick={() => setNotifOpen((v) => !v)} className="relative rounded-xl border border-slate-200 bg-white p-2 text-slate-500 shadow-sm transition hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300" aria-label="Notifications" type="button">
            <Bell size={18} />
            <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-red-500 ring-2 ring-white dark:ring-slate-900" />
          </button>
          {notifOpen && (
            <div className="absolute right-0 mt-2 w-80 rounded-2xl border border-slate-200 bg-white p-3 shadow-xl dark:border-slate-800 dark:bg-slate-900">
              <div className="mb-2 flex items-center justify-between px-1"><h3 className="font-bold text-slate-950 dark:text-white">Notifications</h3><button onClick={() => setNotifOpen(false)}><X size={16}/></button></div>
              <div className="space-y-2">
                {notifications.map((n) => <div key={n.title} className="rounded-xl border border-slate-100 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-950"><p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{n.title}</p><p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{n.message}</p></div>)}
              </div>
              <Link href="/lending/overdue" className="mt-3 flex justify-center rounded-xl bg-indigo-600 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-700">Review operations</Link>
            </div>
          )}
        </div>

        <div className="relative">
          <button onClick={() => setProfileOpen((v) => !v)} className="flex items-center gap-2 rounded-full bg-gradient-to-br from-indigo-600 to-violet-600 px-2 py-1.5 text-sm font-bold text-white shadow-md shadow-indigo-500/20" type="button">
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-white/15">L</span><ChevronDown size={14}/>
          </button>
          {profileOpen && (
            <div className="absolute right-0 mt-2 w-64 rounded-2xl border border-slate-200 bg-white p-3 shadow-xl dark:border-slate-800 dark:bg-slate-900">
              <div className="flex items-center gap-3 border-b border-slate-100 pb-3 dark:border-slate-800"><div className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-600 font-bold text-white">L</div><div><p className="font-bold text-slate-950 dark:text-white">Library Admin</p><p className="text-xs text-slate-500">admin console</p></div></div>
              <button className="mt-2 flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"><UserCircle size={16}/>Profile</button>
              <button className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"><Settings size={16}/>Settings</button>
            </div>
          )}
        </div>
      </div>

      {cmdOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-slate-950/40 px-4 pt-24 backdrop-blur-sm" onMouseDown={() => setCmdOpen(false)}>
          <div className="w-full max-w-xl overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-900" onMouseDown={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-3 border-b border-slate-100 px-4 py-3 dark:border-slate-800"><Search size={18} className="text-slate-400"/><input value={query} onChange={(e) => setQuery(e.target.value)} autoFocus placeholder="Search pages and actions..." className="w-full bg-transparent text-sm outline-none placeholder:text-slate-400 dark:text-slate-100"/><button onClick={() => setCmdOpen(false)}><X size={18}/></button></div>
            <div className="max-h-80 overflow-y-auto p-2">
              {filteredCommands.map(({ label, href, icon: Icon }) => (
                <button key={href} onClick={() => { setCmdOpen(false); setQuery(""); if (pathname !== href) router.push(href); }} className="flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-left text-sm font-semibold text-slate-700 hover:bg-indigo-50 hover:text-indigo-700 dark:text-slate-200 dark:hover:bg-indigo-500/10 dark:hover:text-indigo-300" type="button"><Icon size={17}/>{label}</button>
              ))}
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
