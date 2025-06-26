"""add_subreddit_fundraising_goal_id_to_donations

Revision ID: dcc688aa683c
Revises: 57aff1702698
Create Date: 2025-06-26 14:44:54.537560

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'dcc688aa683c'
down_revision = '57aff1702698'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use batch mode for SQLite
    with op.batch_alter_table('donations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('subreddit_fundraising_goal_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_donations_subreddit_fundraising_goal_id'), ['subreddit_fundraising_goal_id'], unique=False)
        batch_op.create_foreign_key('fk_donations_subreddit_fundraising_goal_id', 'subreddit_fundraising_goals', ['subreddit_fundraising_goal_id'], ['id'])


def downgrade() -> None:
    # Use batch mode for SQLite
    with op.batch_alter_table('donations', schema=None) as batch_op:
        batch_op.drop_constraint('fk_donations_subreddit_fundraising_goal_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_donations_subreddit_fundraising_goal_id'))
        batch_op.drop_column('subreddit_fundraising_goal_id') 