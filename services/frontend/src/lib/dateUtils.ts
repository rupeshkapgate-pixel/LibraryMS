const MS_PER_DAY = 24 * 60 * 60 * 1000;

export type DateOnlyInput = string | Date | null | undefined;

function startOfLocalDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

export function parseDateOnly(dateString: DateOnlyInput): Date | null {
  if (!dateString) return null;

  if (dateString instanceof Date) {
    if (Number.isNaN(dateString.getTime())) return null;
    return startOfLocalDay(dateString);
  }

  const value = String(dateString).trim();
  if (!value) return null;

  const dateOnlyMatch = value.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (dateOnlyMatch) {
    const [, year, month, day] = dateOnlyMatch;
    return new Date(Number(year), Number(month) - 1, Number(day));
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return null;
  return startOfLocalDay(parsed);
}

function todayStart(): Date {
  return startOfLocalDay(new Date());
}

function calendarDayDiff(from: Date, to: Date): number {
  return Math.round((to.getTime() - from.getTime()) / MS_PER_DAY);
}

export function getDaysOverdue(dueDate: DateOnlyInput): number {
  const due = parseDateOnly(dueDate);
  if (!due) return 0;
  return Math.max(0, calendarDayDiff(due, todayStart()));
}

export function isOverdue(dueDate: DateOnlyInput): boolean {
  return getDaysOverdue(dueDate) > 0;
}

export function calculateFine(dueDate: DateOnlyInput, dailyFine = 10): number {
  return getDaysOverdue(dueDate) * dailyFine;
}

export function getDaysRemaining(dueDate: DateOnlyInput): number {
  const due = parseDateOnly(dueDate);
  if (!due) return 0;
  return Math.max(0, calendarDayDiff(todayStart(), due));
}

export function getDueStatusLabel(dueDate: DateOnlyInput): string {
  const overdueDays = getDaysOverdue(dueDate);
  if (overdueDays > 0) return `${overdueDays} days overdue`;

  const remainingDays = getDaysRemaining(dueDate);
  if (remainingDays === 0) return "Due today";
  return `Due in ${remainingDays} days`;
}
