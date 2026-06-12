import { cn } from "@/lib/utils";
export function Spinner({ className }: { className?: string }){return <div className={cn("flex items-center justify-center py-12",className)}><div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-brand-600"/></div>}
export function LoadingSkeleton({rows=5,className}:{rows?:number;className?:string}){return <div className={cn("space-y-3 p-5",className)}>{Array.from({length:rows}).map((_,i)=><div key={i} className="h-12 animate-pulse rounded-xl bg-slate-100"/>)}</div>}
export default LoadingSkeleton;
