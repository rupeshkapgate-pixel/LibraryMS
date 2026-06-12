export interface PaginationMeta { page: number; page_size: number; total_count: number; total_pages: number }
export interface PaginatedResponse<T> { data: T[]; pagination: PaginationMeta }
export interface Book { id: string; title: string; author: string; isbn: string; publisher?: string; category?: string; description?: string; published_year?: number; total_copies: number; available_copies: number; shelf_location?: string; created_at?: string; updated_at?: string }
export interface BookCreate { title: string; author: string; isbn: string; publisher?: string; category?: string; description?: string; published_year?: number; total_copies: number; shelf_location?: string }
export type MembershipStatus = "ACTIVE" | "INACTIVE";
export interface Member { id: string; full_name: string; email: string; phone?: string; address?: string; membership_status: MembershipStatus; created_at?: string; updated_at?: string }
export interface MemberCreate { full_name: string; email: string; phone?: string; address?: string; membership_status?: MembershipStatus }
export type LendingStatus = "BORROWED" | "RETURNED" | "OVERDUE";
export interface LendingRecord { id: string; member_id: string; book_id: string; borrowed_at?: string; due_date?: string; returned_at?: string; status: LendingStatus; fine_amount: number; book_title?: string; book_isbn?: string; member_name?: string; member_email?: string; created_at?: string; updated_at?: string }
export interface BorrowRequest { member_id: string; book_id: string; due_days?: number }
export interface ReturnRequest { lending_id: string }
export interface ReturnResponse { record: LendingRecord; fine_amount: number; is_overdue: boolean; overdue_days: number }
export interface DashboardStats { total_books: number; total_members: number; books_borrowed: number; overdue_books: number }
