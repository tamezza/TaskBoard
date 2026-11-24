"""Add archived flag to boards

Revision ID: 4b47f5aa3c3f
Revises: 35361635a226
Create Date: 2026-11-24 13:38:27.352073

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4b47f5aa3c3f'
down_revision: Union[str, Sequence[str], None] = '35361635a226'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # The column is NOT NULL, so the boards that already exist need a value:
    # server_default makes the database fill them with false.
    op.add_column('boards', sa.Column('archived', sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('boards', 'archived')
