import type { MembershipStatus } from "@/types";
export function MemberStatusBadge({status}:{status:MembershipStatus}){return <span className={status==="ACTIVE"?"badge-green":"badge-gray"}>{status}</span>}
export default MemberStatusBadge;
