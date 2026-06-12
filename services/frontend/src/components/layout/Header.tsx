"use client";

import { Bell } from "lucide-react";
import { API_BASE } from "@/lib/api";

export default function Header() {
  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/85 backdrop-blur">
      <div className="flex h-16 items-center justify-end gap-4 px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          <span className="hidden rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600 sm:inline">
            API: {API_BASE.replace(/^https?:\/\//, "")}
          </span>
          <button
            className="rounded-xl border border-slate-200 p-2 text-slate-500 hover:bg-slate-50"
            aria-label="Notifications"
            type="button"
          >
            <Bell size={18} />
          </button>
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-600 text-sm font-bold text-white">
            L
          </div>
        </div>
      </div>
    </header>
  );
}
