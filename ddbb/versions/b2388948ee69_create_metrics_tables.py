"""create metrics tables

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
        'order_metrics',
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=True),
        sa.Column('instance_id', sa.Integer(), nullable=False),
        sa.Column('simulation_settings', sa.JSON(), nullable=True),
        sa.Column('simulation_policies', sa.JSON(), nullable=True),
        sa.Column('extra_settings', sa.JSON(), nullable=True),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('placement_time', sa.Time(), nullable=True),
        sa.Column('preparation_time', sa.Time(), nullable=True),
        sa.Column('acceptance_time', sa.Time(), nullable=True),
        sa.Column('in_store_time', sa.Time(), nullable=True),
        sa.Column('ready_time', sa.Time(), nullable=True),
        sa.Column('pick_up_time', sa.Time(), nullable=True),
        sa.Column('drop_off_time', sa.Time(), nullable=True),
        sa.Column('expected_drop_off_time', sa.Time(), nullable=True),
        sa.Column('cancellation_time', sa.Time(), nullable=True),
        sa.Column('dropped_off', sa.Boolean(), nullable=True),
        sa.Column('click_to_door_time', sa.Float(), nullable=True),
        sa.Column('click_to_taken_time', sa.Float(), nullable=True),
        sa.Column('ready_to_door_time', sa.Float(), nullable=True),
        sa.Column('ready_to_pick_up_time', sa.Float(), nullable=True),
        sa.Column('in_store_to_pick_up_time', sa.Float(), nullable=True),
        sa.Column('drop_off_lateness_time', sa.Float(), nullable=True),
        sa.Column('click_to_cancel_time', sa.Float(), nullable=True),
    )
    op.create_index('ix_order_metrics_created_at', 'order_metrics', ['created_at'], unique=False)
    op.create_index('ix_order_metrics_instance_id', 'order_metrics', ['instance_id'], unique=False)

    op.create_table(
        'courier_metrics',
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=True),
        sa.Column('instance_id', sa.Integer(), nullable=False),
        sa.Column('simulation_settings', sa.JSON(), nullable=True),
        sa.Column('simulation_policies', sa.JSON(), nullable=True),
        sa.Column('extra_settings', sa.JSON(), nullable=True),
        sa.Column('courier_id', sa.Integer(), nullable=True),
        sa.Column('on_time', sa.Time(), nullable=True),
        sa.Column('off_time', sa.Time(), nullable=True),
        sa.Column('fulfilled_orders', sa.Integer(), nullable=True),
        sa.Column('earnings', sa.Float(), nullable=True),
        sa.Column('utilization_time', sa.Float(), nullable=True),
        sa.Column('accepted_notifications', sa.Integer(), nullable=True),
        sa.Column('guaranteed_compensation', sa.Boolean(), nullable=True),
        sa.Column('courier_utilization', sa.Float(), nullable=True),
        sa.Column('courier_delivery_earnings', sa.Float(), nullable=True),
        sa.Column('courier_compensation', sa.Float(), nullable=True),
        sa.Column('courier_orders_delivered_per_hour', sa.Float(), nullable=True),
        sa.Column('courier_bundles_picked_per_hour', sa.Float(), nullable=True),
    )
    op.create_index('ix_courier_metrics_created_at', 'courier_metrics', ['created_at'], unique=False)
    op.create_index('ix_courier_metrics_instance_id', 'courier_metrics', ['instance_id'], unique=False)

    op.create_table(
        'matching_optimization_metrics',
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=True),
        sa.Column('instance_id', sa.Integer(), nullable=False),
        sa.Column('simulation_settings', sa.JSON(), nullable=True),
        sa.Column('simulation_policies', sa.JSON(), nullable=True),
        sa.Column('extra_settings', sa.JSON(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=True),
        sa.Column('orders', sa.Integer(), nullable=True),
        sa.Column('routes', sa.Integer(), nullable=True),
        sa.Column('couriers', sa.Integer(), nullable=True),
        sa.Column('variables', sa.BigInteger(), nullable=True),
        sa.Column('constraints', sa.BigInteger(), nullable=True),
        sa.Column('routing_time', sa.Float(), nullable=True),
        sa.Column('matching_time', sa.Float(), nullable=True),
        sa.Column('matches', sa.Integer(), nullable=True)
    )
    op.create_index(
        'ix_matching_optimization_metrics_created_at',
        'matching_optimization_metrics',
        ['created_at'],
        unique=False
    )
    op.create_index(
        'ix_matching_optimization_metrics_instance_id',
        'matching_optimization_metrics',
        ['instance_id'],
        unique=False
    )


def downgrade():
    op.drop_table('order_metrics')
    op.drop_index('ix_order_metrics_created_at', table_name='order_metrics')
    op.drop_index('ix_order_metrics_instance_id', table_name='order_metrics')

    op.drop_table('courier_metrics')
    op.drop_index('ix_courier_metrics_created_at', table_name='courier_metrics')
    op.drop_index('ix_courier_metrics_instance_id', table_name='courier_metrics')

    op.drop_table('matching_optimization_metrics')
    op.drop_index('ix_matching_optimization_metrics_created_at', table_name='matching_optimization_metrics')
    op.drop_index('ix_matching_optimization_metrics_instance_id', table_name='matching_optimization_metrics')
