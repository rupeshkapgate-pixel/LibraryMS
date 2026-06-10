# Database Design

## Schema overview

One PostgreSQL 15 instance with three logical schemas:

```sql
librarydb
├── books_db     (owned by book-service)
│   └── books
├── members_db   (owned by member-service)
│   └── members
└── lending_db   (owned by lending-service)
    └── lending_records
```

## books_db.books

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| title | VARCHAR(500) | NOT NULL |
| author | VARCHAR(500) | NOT NULL |
| isbn | VARCHAR(20) | UNIQUE NOT NULL |
| publisher | VARCHAR(300) | |
| category | VARCHAR(100) | |
| description | TEXT | |
| published_year | INTEGER | |
| total_copies | INTEGER | DEFAULT 1 |
| available_copies | INTEGER | DEFAULT 1 |
| shelf_location | VARCHAR(50) | |
| created_at | TIMESTAMP | NOT NULL |
| updated_at | TIMESTAMP | NOT NULL |
| deleted_at | TIMESTAMP | NULL = not deleted (soft delete) |

Indexes: title, author, isbn (unique), category, deleted_at

## members_db.members

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| full_name | VARCHAR(300) | NOT NULL |
| email | VARCHAR(255) | UNIQUE NOT NULL |
| phone | VARCHAR(20) | |
| address | VARCHAR(500) | |
| membership_status | ENUM | ACTIVE / INACTIVE |
| created_at | TIMESTAMP | NOT NULL |
| updated_at | TIMESTAMP | NOT NULL |
| deleted_at | TIMESTAMP | NULL = not deleted |

## lending_db.lending_records

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| member_id | UUID | FK → members (logical, cross-schema) |
| book_id | UUID | FK → books (logical, cross-schema) |
| borrowed_at | TIMESTAMP | NOT NULL |
| due_date | TIMESTAMP | NOT NULL |
| returned_at | TIMESTAMP | NULL = not yet returned |
| status | ENUM | BORROWED / RETURNED / OVERDUE |
| fine_amount | FLOAT | ₹10/day overdue, 0.0 if on-time |
| created_at | TIMESTAMP | NOT NULL |
| updated_at | TIMESTAMP | NOT NULL |

> Note: Cross-schema foreign keys are enforced at application level (not DB level)
> because each service owns its schema independently.

## Fine calculation

```
if returned_at > due_date:
    overdue_days = (returned_at - due_date).days
    fine = overdue_days * 10  # ₹10 per day
else:
    fine = 0.0
```
