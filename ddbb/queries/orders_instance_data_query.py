orders_query = """
    SELECT
        order_id,
        pick_up_lat,
        pick_up_lng,
        drop_off_lat,
        drop_off_lng,
        placement_time,
        preparation_time,
        ready_time,
        expected_drop_off_time
    FROM orders_instance_data
    WHERE placement_time = {placement_time} AND instance_id = {instance_id}
"""
