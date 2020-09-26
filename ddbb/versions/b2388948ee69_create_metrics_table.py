"""create metrics table

Revision ID: b2388948ee69
Revises: 65698a586556
Create Date: 2020-10-02 21:55:35.986237

"""
import sqlalchemy as sa
from alembic import op
# revision identifiers, used by Alembic.
from sqlalchemy import func

revision = 'b2388948ee69'
down_revision = '65698a586556'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'metrics',
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=True),
        sa.Column('instance_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('value', sa.Float(), nullable=True),
        sa.Column('mean', sa.Float(), nullable=True),
        sa.Column('standard_deviation', sa.Float(), nullable=True),
        sa.Column('minimum', sa.Float(), nullable=True),
        sa.Column('tenth_percentile', sa.Float(), nullable=True),
        sa.Column('median', sa.Float(), nullable=True),
        sa.Column('ninetieth_percentile', sa.Float(), nullable=True),
        sa.Column('maximum', sa.Float(), nullable=True),
    )
    op.create_index('ix_metrics_created_at', 'metrics', ['created_at'], unique=False)
    op.create_index('ix_metrics_instance_id', 'metrics', ['instance_id'], unique=False)
    op.create_index('ix_metrics_name', 'metrics', ['name'], unique=False)


def downgrade():
    op.drop_table('metrics')
    op.drop_index('ix_metrics_created_at', table_name='metrics')
    op.drop_index('ix_metrics_instance_id', table_name='metrics')
