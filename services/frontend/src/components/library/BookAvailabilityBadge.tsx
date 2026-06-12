import { cn } from "@/lib/utils";
export function BookAvailabilityBadge({available,total}:{available:number;total:number}){const status=available<=0?"Unavailable":available<=Math.max(1,Math.ceil(total*0.25))?"Low Stock":"Available";const cls=status==="Available"?"badge-green":status==="Low Stock"?"badge-yellow":"badge-red";return <span className={cn(cls)}>{status}</span>}
export default BookAvailabilityBadge;
