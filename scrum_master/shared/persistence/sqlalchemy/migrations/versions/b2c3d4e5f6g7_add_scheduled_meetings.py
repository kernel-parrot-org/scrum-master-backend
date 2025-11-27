"""Add scheduled_meetings table

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2024-11-26 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum type (use raw SQL with IF NOT EXISTS)
    op.execute("DO $$ BEGIN CREATE TYPE scheduletype AS ENUM ('once', 'daily', 'weekly', 'calendar'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    
    # Create table using existing enum
    op.create_table(
        'scheduled_meetings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('meet_url', sa.String(512), nullable=False),
        sa.Column('bot_name', sa.String(255), nullable=False, server_default='Scrum Bot'),
        sa.Column('schedule_type', postgresql.ENUM('once', 'daily', 'weekly', 'calendar', name='scheduletype', create_type=False), nullable=False, server_default='once'),
        sa.Column('scheduled_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('days_of_week', sa.String(20), nullable=True),
        sa.Column('calendar_event_id', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_trigger_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Create indexes
    op.create_index('ix_scheduled_meetings_user_id', 'scheduled_meetings', ['user_id'])
    op.create_index('ix_scheduled_meetings_next_trigger', 'scheduled_meetings', ['next_trigger_at', 'is_active'])


def downgrade() -> None:
    op.drop_index('ix_scheduled_meetings_next_trigger', table_name='scheduled_meetings')
    op.drop_index('ix_scheduled_meetings_user_id', table_name='scheduled_meetings')
    op.drop_table('scheduled_meetings')
    
    # Drop enum type
    op.execute("DROP TYPE IF EXISTS scheduletype;")
