import type { ButtonHTMLAttributes } from "react"; import { cn } from "@/lib/utils";
type Variant="primary"|"secondary"|"danger"|"ghost";
export function Button({className,variant="primary",...props}:ButtonHTMLAttributes<HTMLButtonElement>&{variant?:Variant}){const v={primary:"btn-primary",secondary:"btn-secondary",danger:"btn-danger",ghost:"btn-ghost"}[variant];return <button className={cn(v,className)} {...props}/>}
export default Button;
