"""seed_subreddits_table

Revision ID: cac58179b196
Revises: 3d8aa5ef0b11
Create Date: 2025-07-14 19:53:24.564978

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cac58179b196'
down_revision: Union[str, Sequence[str], None] = '3d8aa5ef0b11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed the subreddits table with initial subreddit list."""
    # Define the initial subreddit list from the codebase
    initial_subreddits = [
        # Nature & Outdoors
        "nature", "earthporn", "landscapephotography", "hiking", "camping", 
        "gardening", "plants", "succulents",
        # Space & Science
        "space", "astrophotography", "nasa", "science", "physics", "chemistry", "biology",
        # Sports & Recreation
        "golf", "soccer", "basketball", "tennis", "baseball", "hockey", 
        "fishing", "surfing", "skiing", "rockclimbing",
        # Animals & Pets
        "aww", "cats", "dogs", "puppies", "kittens", "wildlife", "birding", "aquariums",
        # Food & Cooking
        "food", "foodporn", "cooking", "baking", "coffee", "tea", "wine",
        # Art & Design
        "art", "design", "architecture", "interiordesign", "streetart", "digitalart",
        # Technology & Gaming
        "programming", "gaming", "pcgaming", "retrogaming", "cyberpunk", "futurology",
        # Travel & Culture
        "travel", "backpacking", "photography", "cityporn", "history",
        # Lifestyle & Wellness
        "fitness", "yoga", "meditation", "minimalism", "sustainability", "vegan",
    ]
    
    # Create table reference
    subreddits_table = sa.table('subreddits',
        sa.column('subreddit_name', sa.String),
        sa.column('display_name', sa.String),
        sa.column('over18', sa.Boolean),
        sa.column('spoilers_enabled', sa.Boolean),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime)
    )
    
    # Insert initial subreddits
    from datetime import datetime, timezone
    current_time = datetime.now(timezone.utc)
    
    # Only insert if subreddits don't already exist
    connection = op.get_bind()
    
    for subreddit_name in initial_subreddits:
        # Check if subreddit already exists
        result = connection.execute(
            sa.text("SELECT COUNT(*) FROM subreddits WHERE subreddit_name = :name"),
            {"name": subreddit_name}
        ).scalar()
        
        if result == 0:
            op.execute(
                subreddits_table.insert().values(
                    subreddit_name=subreddit_name,
                    display_name=subreddit_name,
                    over18=False,
                    spoilers_enabled=False,
                    created_at=current_time,
                    updated_at=current_time
                )
            )


def downgrade() -> None:
    """Remove seeded subreddits from the table."""
    # Define the same subreddit list for removal
    initial_subreddits = [
        # Nature & Outdoors
        "nature", "earthporn", "landscapephotography", "hiking", "camping", 
        "gardening", "plants", "succulents",
        # Space & Science
        "space", "astrophotography", "nasa", "science", "physics", "chemistry", "biology",
        # Sports & Recreation
        "golf", "soccer", "basketball", "tennis", "baseball", "hockey", 
        "fishing", "surfing", "skiing", "rockclimbing",
        # Animals & Pets
        "aww", "cats", "dogs", "puppies", "kittens", "wildlife", "birding", "aquariums",
        # Food & Cooking
        "food", "foodporn", "cooking", "baking", "coffee", "tea", "wine",
        # Art & Design
        "art", "design", "architecture", "interiordesign", "streetart", "digitalart",
        # Technology & Gaming
        "programming", "gaming", "pcgaming", "retrogaming", "cyberpunk", "futurology",
        # Travel & Culture
        "travel", "backpacking", "photography", "cityporn", "history",
        # Lifestyle & Wellness
        "fitness", "yoga", "meditation", "minimalism", "sustainability", "vegan",
    ]
    
    # Remove only the initial subreddits (in case custom ones were added)
    for subreddit_name in initial_subreddits:
        op.execute(
            sa.text("DELETE FROM subreddits WHERE subreddit_name = :name"),
            {"name": subreddit_name}
        )
