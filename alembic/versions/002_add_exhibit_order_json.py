"""Add exhibit_order_json to sessions

Revision ID: 002_add_exhibit_order_json
Revises: 001_initial_schema
Create Date: 2025-11-09 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_add_exhibit_order_json'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add exhibit_order_json column to sessions table
    op.add_column('sessions', sa.Column('exhibit_order_json', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove exhibit_order_json column from sessions table
    op.drop_column('sessions', 'exhibit_order_json')
