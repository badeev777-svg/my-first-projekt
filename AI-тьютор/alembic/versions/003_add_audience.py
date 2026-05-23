"""Add audience field to users

Revision ID: 003
Revises: 002
Create Date: 2026-05-23 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('audience', sa.String(10), nullable=False, server_default='adults'))


def downgrade() -> None:
    op.drop_column('users', 'audience')
