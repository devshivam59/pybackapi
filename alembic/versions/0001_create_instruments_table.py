"""Create instruments table

Revision ID: 0001
Revises:
Create Date: 2025-10-06 10:33:17.641644

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'instruments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('instrument_token', sa.BigInteger(), nullable=True),
        sa.Column('exchange_token', sa.String(), nullable=True),
        sa.Column('tradingsymbol', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('last_price', sa.Float(), nullable=True),
        sa.Column('expiry', sa.String(), nullable=True),
        sa.Column('strike', sa.Float(), nullable=True),
        sa.Column('tick_size', sa.Float(), nullable=True),
        sa.Column('lot_size', sa.Integer(), nullable=True),
        sa.Column('instrument_type', sa.String(), nullable=True),
        sa.Column('segment', sa.String(), nullable=True),
        sa.Column('exchange', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_instruments_id'), 'instruments', ['id'], unique=False)
    op.create_index(op.f('ix_instruments_instrument_token'), 'instruments', ['instrument_token'], unique=True)
    op.create_index(op.f('ix_instruments_name'), 'instruments', ['name'], unique=False)
    op.create_index(op.f('ix_instruments_tradingsymbol'), 'instruments', ['tradingsymbol'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_instruments_tradingsymbol'), table_name='instruments')
    op.drop_index(op.f('ix_instruments_name'), table_name='instruments')
    op.drop_index(op.f('ix_instruments_instrument_token'), table_name='instruments')
    op.drop_index(op.f('ix_instruments_id'), table_name='instruments')
    op.drop_table('instruments')