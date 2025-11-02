"""Initial schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2025-11-02 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create exhibits table
    op.create_table('exhibits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('text_md', sa.String(), nullable=False),
        sa.Column('audio_path', sa.String(), nullable=True),
        sa.Column('audio_transcript', sa.String(), nullable=True),
        sa.Column('master_image', sa.String(), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_exhibits_order_index'), 'exhibits', ['order_index'], unique=False)
    op.create_index(op.f('ix_exhibits_slug'), 'exhibits', ['slug'], unique=True)

    # Create sessions table
    op.create_table('sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.Uuid(), nullable=False),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('accept_lang', sa.String(), nullable=True),
        sa.Column('completed', sa.Boolean(), nullable=False),
        sa.Column('selfeval_json', sa.JSON(), nullable=True),
        sa.Column('exhibition_feedback_json', sa.JSON(), nullable=True),
        sa.Column('last_activity', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sessions_uuid'), 'sessions', ['uuid'], unique=True)

    # Create images table
    op.create_table('images',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('exhibit_id', sa.Integer(), nullable=False),
        sa.Column('path', sa.String(), nullable=False),
        sa.Column('alt_text', sa.String(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['exhibit_id'], ['exhibits.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create questions table
    op.create_table('questions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('exhibit_id', sa.Integer(), nullable=True),
        sa.Column('text', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('options_json', sa.JSON(), nullable=True),
        sa.Column('required', sa.Boolean(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['exhibit_id'], ['exhibits.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sqlite_autoincrement=True
    )

    # Create answers table
    op.create_table('answers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('value_text', sa.String(), nullable=True),
        sa.Column('value_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create events table
    op.create_table('events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('exhibit_id', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['exhibit_id'], ['exhibits.id'], ),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('events')
    op.drop_table('answers')
    op.drop_table('questions')
    op.drop_table('images')
    op.drop_index(op.f('ix_sessions_uuid'), table_name='sessions')
    op.drop_table('sessions')
    op.drop_index(op.f('ix_exhibits_slug'), table_name='exhibits')
    op.drop_index(op.f('ix_exhibits_order_index'), table_name='exhibits')
    op.drop_table('exhibits')
