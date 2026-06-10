"""001 initial schema — lending_db

Revision ID: 001
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
    op.execute("CREATE SCHEMA IF NOT EXISTS lending_db")
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE lending_db.lendingstatus AS ENUM ('BORROWED', 'RETURNED', 'OVERDUE'); "
        "EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )
    op.create_table(
        "lending_records",
        sa.Column("id",          UUID(as_uuid=True), primary_key=True),
        sa.Column("member_id",   UUID(as_uuid=True), nullable=False),
        sa.Column("book_id",     UUID(as_uuid=True), nullable=False),
        sa.Column("borrowed_at", sa.DateTime, nullable=False),
        sa.Column("due_date",    sa.DateTime, nullable=False),
        sa.Column("returned_at", sa.DateTime, nullable=True),
        sa.Column("status",
                  sa.Enum("BORROWED", "RETURNED", "OVERDUE", name="lendingstatus", schema="lending_db"),
                  nullable=False, server_default="BORROWED"),
        sa.Column("fine_amount", sa.Float,    nullable=False, server_default="0.0"),
        sa.Column("created_at",  sa.DateTime, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",  sa.DateTime, nullable=False, server_default=sa.text("now()")),
        schema="lending_db",
    )
    op.create_index("ix_lending_member_id", "lending_records", ["member_id"], schema="lending_db")
    op.create_index("ix_lending_book_id",   "lending_records", ["book_id"],   schema="lending_db")
    op.create_index("ix_lending_status",    "lending_records", ["status"],    schema="lending_db")
    op.create_index("ix_lending_due_date",  "lending_records", ["due_date"],  schema="lending_db")


def downgrade() -> None:
    op.drop_table("lending_records", schema="lending_db")
    op.execute("DROP TYPE IF EXISTS lending_db.lendingstatus")
