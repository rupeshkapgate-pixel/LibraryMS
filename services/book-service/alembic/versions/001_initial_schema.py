"""001 initial schema — books_db

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS books_db")
    op.create_table(
        "books",
        sa.Column("id",               UUID(as_uuid=True), primary_key=True),
        sa.Column("title",            sa.String(500),  nullable=False),
        sa.Column("author",           sa.String(500),  nullable=False),
        sa.Column("isbn",             sa.String(20),   nullable=False, unique=True),
        sa.Column("publisher",        sa.String(300),  nullable=True),
        sa.Column("category",         sa.String(100),  nullable=True),
        sa.Column("description",      sa.Text,         nullable=True),
        sa.Column("published_year",   sa.Integer,      nullable=True),
        sa.Column("total_copies",     sa.Integer,      nullable=False, server_default="1"),
        sa.Column("available_copies", sa.Integer,      nullable=False, server_default="1"),
        sa.Column("shelf_location",   sa.String(50),   nullable=True),
        sa.Column("created_at",       sa.DateTime,     nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",       sa.DateTime,     nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at",       sa.DateTime,     nullable=True),
        sa.CheckConstraint("length(trim(title)) > 0", name="ck_books_title_not_blank"),
        sa.CheckConstraint("length(trim(author)) > 0", name="ck_books_author_not_blank"),
        sa.CheckConstraint("length(trim(isbn)) >= 10", name="ck_books_isbn_min_length"),
        sa.CheckConstraint("total_copies >= 0", name="ck_books_total_copies_non_negative"),
        sa.CheckConstraint("available_copies >= 0", name="ck_books_available_copies_non_negative"),
        sa.CheckConstraint("available_copies <= total_copies", name="ck_books_available_not_greater_than_total"),
        sa.CheckConstraint(
            "published_year IS NULL OR published_year BETWEEN 1000 AND 9999",
            name="ck_books_published_year_valid",
        ),
        schema="books_db",
    )
    op.create_index("ix_books_title",      "books", ["title"],    schema="books_db")
    op.create_index("ix_books_author",     "books", ["author"],   schema="books_db")
    op.create_index("ix_books_isbn",       "books", ["isbn"],     schema="books_db", unique=True)
    op.create_index("ix_books_category",   "books", ["category"], schema="books_db")
    op.create_index("ix_books_deleted_at", "books", ["deleted_at"], schema="books_db")


def downgrade() -> None:
    op.drop_table("books", schema="books_db")
