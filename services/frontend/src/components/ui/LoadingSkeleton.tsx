import { cn } from "@/lib/utils";
export function Spinner({ className }: { className?: string }){return <div className={cn("flex items-center justify-center py-12",className)}><div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-indigo-600 dark:border-slate-800 dark:border-t-indigo-400"/></div>}
export function LoadingSkeleton({rows=5,className}:{rows?:number;className?:string}){return <div className={cn("space-y-3 p-5",className)}>{Array.from({length:rows}).map((_,i)=><div key={i} className="h-12 animate-pulse rounded-xl bg-gradient-to-r from-slate-100 via-slate-50 to-slate-100 dark:from-slate-800 dark:via-slate-900 dark:to-slate-800"/>)}</div>}
export default LoadingSkeleton;
