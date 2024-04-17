"""smoelen

Revision ID: 5dff294b1b4c
Revises: d870455eec92
Create Date: 2024-04-17 20:38:11.285331

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5dff294b1b4c'
down_revision: Union[str, None] = 'd870455eec92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('smoelen',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('preview_id', sa.Uuid(), nullable=True),
    sa.ForeignKeyConstraint(['preview_id'], ['items.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_smoelen_id'), 'smoelen', ['id'], unique=False)
    op.create_table('association',
    sa.Column('item_id', sa.Uuid(), nullable=True),
    sa.Column('smoel_id', sa.Uuid(), nullable=True),
    sa.ForeignKeyConstraint(['item_id'], ['items.id'], ),
    sa.ForeignKeyConstraint(['smoel_id'], ['smoelen.id'], )
    )
    op.add_column('items', sa.Column('processed', sa.Boolean(), server_default=sa.text('0'), nullable=False))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('items', 'processed')
    op.drop_table('association')
    op.drop_index(op.f('ix_smoelen_id'), table_name='smoelen')
    op.drop_table('smoelen')
    # ### end Alembic commands ###
