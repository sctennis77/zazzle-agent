"""merge_heads

Revision ID: e3964a8a848e
Revises: 199317be58cb, d848fa9e3ee9
Create Date: 2025-07-19 13:48:43.368320

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3964a8a848e'
down_revision: Union[str, Sequence[str], None] = ('199317be58cb', 'd848fa9e3ee9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
