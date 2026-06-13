"""001 initial schema — members_db

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
    op.execute("CREATE SCHEMA IF NOT EXISTS members_db")
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE members_db.membershipstatus AS ENUM ('ACTIVE', 'INACTIVE'); "
        "EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )
    op.create_table(
        "members",
        sa.Column("id",                UUID(as_uuid=True), primary_key=True),
        sa.Column("full_name",         sa.String(300), nullable=False),
        sa.Column("email",             sa.String(255), nullable=False, unique=True),
        sa.Column("phone",             sa.String(20),  nullable=True),
        sa.Column("address",           sa.String(500), nullable=True),
        sa.Column("membership_status",
                  sa.Enum("ACTIVE", "INACTIVE", name="membershipstatus", schema="members_db"),
                  nullable=False, server_default="ACTIVE"),
        sa.Column("created_at",        sa.DateTime, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",        sa.DateTime, nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at",        sa.DateTime, nullable=True),
        sa.CheckConstraint("length(trim(full_name)) > 0", name="ck_members_full_name_not_blank"),
        sa.CheckConstraint("length(trim(email)) > 3", name="ck_members_email_not_blank"),
        schema="members_db",
    )
    op.create_index("ix_members_email",      "members", ["email"],             schema="members_db", unique=True)
    op.create_index("ix_members_status",     "members", ["membership_status"], schema="members_db")
    op.create_index("ix_members_deleted_at", "members", ["deleted_at"],        schema="members_db")


def downgrade() -> None:
    op.drop_table("members", schema="members_db")
    op.execute("DROP TYPE IF EXISTS members_db.membershipstatus")
