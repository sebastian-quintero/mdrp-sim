from utils.datetime_utils import min_to_sec

# Simulation
COURIER_MIN_ACCEPTANCE_RATE = 0.3
COURIER_MOVEMENT_PROBABILITY = 0.1
COURIER_WAIT_TO_MOVE = min_to_sec(10)
COURIER_WAIT_TO_ACCEPT = 20

DISPATCHER_WAIT_TO_CANCEL = min_to_sec(10)
DISPATCHER_ROLLING_HORIZON_TIME = min_to_sec(1)

ORDER_MAX_PICK_UP_SERVICE_TIME = min_to_sec(10)
ORDER_MAX_DROP_OFF_SERVICE_TIME = min_to_sec(5)

USER_WAIT_TO_CANCEL = min_to_sec(15)
USER_CANCELLATION_PROBABILITY = 0.9
