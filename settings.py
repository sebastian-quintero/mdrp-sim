from utils.datetime_utils import min_to_sec

# Project
VERBOSE_LOGS = True  # Enable / Disable specific (verbose) actor and policy logs

# Simulation
COURIER_MIN_ACCEPTANCE_RATE = 0.3  # Minimum acceptance rate for any courier
COURIER_MOVEMENT_PROBABILITY = 0.1  # Probability that a courier WILL move
COURIER_WAIT_TO_MOVE = min_to_sec(10)  # Time [sec] that a courier waits before deciding to move
COURIER_WAIT_TO_ACCEPT = 20  # Time [sec] that a courier waits before accepting / rejecting a notification
COURIER_EARNINGS_PER_ORDER = 3  # Money earned for dropping off an order
COURIER_EARNINGS_PER_HOUR = 8  # Rate at which the courier can be compensated per hour

DISPATCHER_WAIT_TO_CANCEL = min_to_sec(10)  # Time [sec] to cancel an order, after user wait
DISPATCHER_ROLLING_HORIZON_TIME = min_to_sec(2)  # Time [sec] to buffer orders
DISPATCHER_PREPOSITIONING_TIME = min_to_sec(13)  # Time [sec] to send prepositioning, after buffer time
DISPATCHER_PROSPECTS_MAX_DISTANCE = 3  # Maximum distance [km] between a courier and a store to be considered prospect
DISPATCHER_PROSPECTS_MAX_ORDERS = 3  # Maximum number of orders a courier can carry simultaneously

ORDER_MAX_PICK_UP_SERVICE_TIME = min_to_sec(10)  # Maximum service time [sec] at the pick up location
ORDER_MAX_DROP_OFF_SERVICE_TIME = min_to_sec(5)  # Maximum service time [sec] at the drop off location
ORDER_MIN_SERVICE_TIME = min_to_sec(2)  # Minimum service time [sec] at either a pick up or drop off location

USER_WAIT_TO_CANCEL = min_to_sec(15)  # Time [sec] that a user waits before deciding to cancel an order
USER_CANCELLATION_PROBABILITY = 0.9  # Probability that a user will cancel an order if no courier is assigned
