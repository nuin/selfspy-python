"""add session tracking and focus time

Revision ID: 6131b92d3ab4
Revises: 
Create Date: 2025-11-23 23:08:14.740159

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6131b92d3ab4'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create session table
    op.create_table(
        'session',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('total_keystrokes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_clicks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('active_seconds', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('idle_seconds', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('hostname', sa.String(), nullable=True),
        sa.Column('platform', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    # Add indexes on session
    op.create_index('ix_session_start_time', 'session', ['start_time'])
    op.create_index('ix_session_end_time', 'session', ['end_time'])

    # Add new columns to window table with batch mode for SQLite
    with op.batch_alter_table('window', schema=None) as batch_op:
        batch_op.add_column(sa.Column('session_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('focus_seconds', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('last_activity_at', sa.DateTime(), nullable=True))
        batch_op.create_foreign_key('fk_window_session', 'session', ['session_id'], ['id'])
        batch_op.create_index('ix_window_session_id', ['session_id'])


def downgrade() -> None:
    # Remove columns from window table
    with op.batch_alter_table('window', schema=None) as batch_op:
        batch_op.drop_index('ix_window_session_id')
        batch_op.drop_constraint('fk_window_session', type_='foreignkey')
        batch_op.drop_column('last_activity_at')
        batch_op.drop_column('focus_seconds')
        batch_op.drop_column('session_id')

    # Drop session table indexes and table
    op.drop_index('ix_session_end_time', 'session')
    op.drop_index('ix_session_start_time', 'session')
    op.drop_table('session')
