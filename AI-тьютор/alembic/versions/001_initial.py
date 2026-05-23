"""Initial migration: users, dialogs, daily_limits, subscriptions

Revision ID: 001
Revises:
Create Date: 2026-05-16 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(255), nullable=True),
        sa.Column('first_name', sa.String(255), nullable=False),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('level', sa.String(3), nullable=False, server_default='A1'),
        sa.Column('goal', sa.String(50), nullable=True),
        sa.Column('format', sa.String(10), nullable=False, server_default='text'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('premium_until', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('user_id')
    )

    op.create_table(
        'dialogs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('scenario', sa.String(50), nullable=False),
        sa.Column('level', sa.String(3), nullable=False),
        sa.Column('messages', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'daily_limits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'date', name='uq_user_date')
    )

    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('plan', sa.String(20), nullable=False),
        sa.Column('payment_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_dialogs_user_id'), 'dialogs', ['user_id'], unique=False)
    op.create_index(op.f('ix_daily_limits_user_id'), 'daily_limits', ['user_id'], unique=False)
    op.create_index(op.f('ix_subscriptions_user_id'), 'subscriptions', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_subscriptions_user_id'), table_name='subscriptions')
    op.drop_index(op.f('ix_daily_limits_user_id'), table_name='daily_limits')
    op.drop_index(op.f('ix_dialogs_user_id'), table_name='dialogs')
    op.drop_table('subscriptions')
    op.drop_table('daily_limits')
    op.drop_table('dialogs')
    op.drop_table('users')
