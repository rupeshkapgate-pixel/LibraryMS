import type { LendingStatus } from "@/types";
export function LendingStatusBadge({status}:{status:LendingStatus}){const cls=status==="BORROWED"?"badge-blue":status==="RETURNED"?"badge-green":"badge-red";return <span className={cls}>{status}</span>}
export default LendingStatusBadge;
