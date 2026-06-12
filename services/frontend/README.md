# Library Management Frontend

Production-style Next.js admin dashboard for the Library Management System.

## Environment

Create `.env.local` when running outside Docker:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

The API client also supports the previous `NEXT_PUBLIC_API_URL` variable as a fallback to avoid breaking older setups.

## Run locally

```bash
npm install
npm run lint
npm run build
npm run dev
```

## Docker validation

From the repository root, run:

```bash
docker compose up --build
```

## Frontend screenshots

Add interview/demo screenshots here after running the app:

- Dashboard overview: `docs/screenshots/dashboard.png`
- Books catalogue: `docs/screenshots/books.png`
- Members management: `docs/screenshots/members.png`
- Borrow workflow: `docs/screenshots/borrow-book.png`
- Return workflow: `docs/screenshots/return-book.png`
- Overdue books: `docs/screenshots/overdue-books.png`

## UI checklist

- Modern SaaS-style shell with sidebar and top header
- Responsive navigation with mobile drawer
- Dashboard stat cards, activity table, quick actions, and service status
- Search, filters, sorting, badges, skeletons, empty states, and error states
- Confirmation dialogs for destructive actions
- Toast notifications for mutations
- Centralized typed API client using environment variable configuration
