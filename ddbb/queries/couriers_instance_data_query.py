couriers_query = """
    SELECT
        courier_id,
        vehicle,
        on_lat,
        on_lng,
        on_time,
        off_time
    FROM couriers_instance_data
    WHERE on_time = {on_time} AND instance_id = {instance_id}
"""