import { clsx, type ClassValue } from "clsx"; import { twMerge } from "tailwind-merge";
export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)); }
export function formatDate(iso?: string | null): string { if (!iso) return "—"; try { return new Date(iso).toLocaleDateString("en-IN", { day:"2-digit", month:"short", year:"numeric" }); } catch { return iso; } }
export function formatDateTime(iso?: string | null): string { if (!iso) return "—"; try { return new Date(iso).toLocaleString("en-IN", { day:"2-digit", month:"short", year:"numeric", hour:"2-digit", minute:"2-digit" }); } catch { return iso; } }
export function formatCurrency(amount: number): string { return `₹${Number(amount || 0).toFixed(2)}`; }
export function isOverdue(dueDate?: string | null): boolean { if (!dueDate) return false; return new Date(dueDate) < new Date(); }
export function daysOverdue(dueDate?: string | null): number { if (!dueDate) return 0; const diff = Date.now() - new Date(dueDate).getTime(); return Math.max(0, Math.ceil(diff / 86400000)); }
export function daysRemaining(dueDate?: string | null): number { if (!dueDate) return 0; return Math.ceil((new Date(dueDate).getTime() - Date.now()) / 86400000); }
export function shortId(id?: string) { return id ? `${id.slice(0, 8)}…` : "—"; }
