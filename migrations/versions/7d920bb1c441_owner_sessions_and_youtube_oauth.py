"""Owner sessions and encrypted YouTube OAuth credentials.

Revision ID: 7d920bb1c441
Revises: f05b1bece7d8
"""

import sqlalchemy as sa
from alembic import op

revision = "7d920bb1c441"
down_revision = "f05b1bece7d8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "owner_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("secret_version", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_owner_sessions_expires_at", "owner_sessions", ["expires_at"])
    op.create_table(
        "oauth_flows",
        sa.Column("state_hash", sa.String(64), primary_key=True),
        sa.Column(
            "owner_session_hash",
            sa.String(64),
            sa.ForeignKey("owner_sessions.token_hash"),
            nullable=False,
        ),
        sa.Column("verifier_encrypted", sa.Text(), nullable=False),
        sa.Column("expected_channel_id", sa.String(100), nullable=False),
        sa.Column("redirect_uri", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_oauth_flows_expires_at", "oauth_flows", ["expires_at"])
    op.create_table(
        "oauth_credentials",
        sa.Column(
            "account_id", sa.String(36), sa.ForeignKey("social_accounts.id"), primary_key=True
        ),
        sa.Column("credentials_encrypted", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("oauth_credentials")
    op.drop_index("ix_oauth_flows_expires_at", table_name="oauth_flows")
    op.drop_table("oauth_flows")
    op.drop_index("ix_owner_sessions_expires_at", table_name="owner_sessions")
    op.drop_table("owner_sessions")
