"""create instance data tables

Revision ID: 65698a586556
Revises: 
Create Date: 2020-09-25 01:54:58.352259

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '65698a586556'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'orders_instance_data',
        sa.Column('instance_id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('pick_up_lat', sa.Float(), nullable=False),
        sa.Column('pick_up_lng', sa.Float(), nullable=False),
        sa.Column('drop_off_lat', sa.Float(), nullable=False),
        sa.Column('drop_off_lng', sa.Float(), nullable=False),
        sa.Column('placement_time', sa.Time(), nullable=False),
        sa.Column('preparation_time', sa.Time(), nullable=False),
        sa.Column('ready_time', sa.Time(), nullable=False),
        sa.Column('expected_drop_off_time', sa.Time(), nullable=False),
    )
    op.create_index('ix_orders_instance_data_instance_id', 'orders_instance_data', ['instance_id'], unique=False)
    op.create_index('ix_orders_instance_data_placement_time', 'orders_instance_data', ['placement_time'], unique=False)

    op.create_table(
        'couriers_instance_data',
        sa.Column('instance_id', sa.Integer(), nullable=False),
        sa.Column('courier_id', sa.Integer(), nullable=False),
        sa.Column('vehicle', sa.String(), nullable=False),
        sa.Column('on_lat', sa.Float(), nullable=False),
        sa.Column('on_lng', sa.Float(), nullable=False),
        sa.Column('on_time', sa.Time(), nullable=False),
        sa.Column('off_time', sa.Time(), nullable=False),
    )
    op.create_index('ix_couriers_instance_data_instance_id', 'couriers_instance_data', ['instance_id'], unique=False)
    op.create_index('ix_couriers_instance_data_on_time', 'couriers_instance_data', ['on_time'], unique=False)


def downgrade():
    op.drop_table('orders_instance_data')
    op.drop_index('ix_orders_instance_data_instance_id', table_name='orders_instance_data')
    op.drop_index('ix_orders_instance_data_placement_time', table_name='orders_instance_data')

    op.drop_table('couriers_instance_data')
    op.drop_index('ix_couriers_instance_data_instance_id', table_name='couriers_instance_data')
    op.drop_index('ix_couriers_instance_data_on_time', table_name='couriers_instance_data')
