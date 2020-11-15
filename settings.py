from datetime import time
from typing import Union, Optional

from utils.datetime_utils import min_to_sec, hour_to_sec

# Project
INSTANCE: int = 3  # Desired instance to be simulated
VERBOSE_LOGS: bool = False  # Enable / Disable specific (verbose) actor and policy logs
SEED: Optional[Union[float, int]] = 8795  # [Optional] Seed for running the simulation. Can be None.

DB_USERNAME: str = 'docker'  # DDBB Username
DB_PASSWORD: str = 'docker'  # DDBB Password
DB_HOST: str = '127.0.0.1'  # DDBB Host
DB_PORT: str = '5432'  # DDBB Port
DB_DATABASE: str = 'mdrp_sim'  # DDBB Name

# Simulation Constants
SIMULATE_FROM: time = time(7, 0, 0)  # Simulate from this time on
SIMULATE_UNTIL: time = time(12, 0, 0)  # Simulate until this time
CREATE_USERS_UNTIL: time = time(11, 0, 0)  # Create new users to submit orders until this time
CREATE_COURIERS_UNTIL: time = time(9, 0, 0)  # Create new couriers to log on until this time
WARM_UP_TIME: float = hour_to_sec(1) + min_to_sec(30)  # Warm up time [sec] to achieve steady state simulation

# Simulation Policies
#   Dispatcher
DISPATCHER_CANCELLATION_POLICY: str = 'static'  # Policy for canceling orders. Options: ['static']
DISPATCHER_BUFFERING_POLICY: str = 'rolling_horizon'  # Policy for buffering orders: Options: ['rolling_horizon']
DISPATCHER_PREPOSITIONING_EVALUATION_POLICY: str = 'fixed'  # Policy for the prepositioning timing. Options: ['fixed']
DISPATCHER_PREPOSITIONING_POLICY: str = 'naive'  # Policy for prepositioning couriers. Options: ['naive']
DISPATCHER_MATCHING_POLICY: str = 'mdrp'  # Policy for matching orders and couriers. Options: ['greedy', 'mdrp', 'mdrp_graph', 'mdrp_graph_prospects', 'modified_mdrp']
#   Courier
COURIER_ACCEPTANCE_POLICY: str = 'uniform'  # Policy for accepting a notification. Options: ['uniform', 'absolute']
COURIER_MOVEMENT_EVALUATION_POLICY: str = 'neighbors'  # Policy to determine if the courier wants to relocate. Options: ['neighbors', 'still']
COURIER_MOVEMENT_POLICY: str = 'osrm'  # Policy that models the movement of a courier about the city. Options: ['osrm']
#   User
USER_CANCELLATION_POLICY: str = 'random'  # Policy to decide if a user wants to cancel an order. Options: ['random']

# Simulation Policies Configuration
#   Courier
#       Courier Acceptance Policy
COURIER_MIN_ACCEPTANCE_RATE: float = 0.9  # Minimum acceptance rate for any courier
COURIER_WAIT_TO_ACCEPT: float = 20  # Time [sec] that a courier waits before accepting / rejecting a notification
#       Courier Movement Evaluation Policy
COURIER_MOVEMENT_PROBABILITY: float = 0.5  # Probability that a courier WILL move
COURIER_WAIT_TO_MOVE: float = min_to_sec(40)  # Time [sec] that a courier waits before deciding to move
#       Other Constants
COURIER_EARNINGS_PER_ORDER: float = 3  # Money earned for dropping off an order
COURIER_EARNINGS_PER_HOUR: float = 8  # Rate at which the courier can be compensated per hour

#   Dispatcher
#       Cancellation Policy
DISPATCHER_WAIT_TO_CANCEL: float = min_to_sec(55)  # Time [sec] to cancel an order
#       Buffering Policy
DISPATCHER_ROLLING_HORIZON_TIME: float = min_to_sec(5)  # Time [sec] to buffer orders
#       Prepositioning Evaluation Policy
DISPATCHER_PREPOSITIONING_TIME: float = hour_to_sec(1)  # Time [sec] to execute prepositioning
#       Matching Policy
DISPATCHER_PROSPECTS_MAX_DISTANCE: float = 3  # Maximum distance [km] between a courier and a store
DISPATCHER_PROSPECTS_MAX_ORDERS: int = 3  # Maximum number of orders a courier can carry simultaneously
DISPATCHER_PROSPECTS_MAX_STOP_OFFSET: float = min_to_sec(10)  # Max offset time [sec] from a stop's expected timestamp
DISPATCHER_PROSPECTS_MAX_READY_TIME: float = min_to_sec(4)  # Time [sec] for ready route before avoiding stop offset
DISPATCHER_MYOPIC_READY_TIME_SLACK: int = min_to_sec(10)  # Time [sec] to consider ready orders for target bundle size
DISPATCHER_GEOHASH_PRECISION_GROUPING: int = 8  # Precision to group orders into a proxy of stores
DISPATCHER_DELAY_PENALTY: float = 0.4  # Constant penalty for delays in the pick up of a bundle of orders

#   User
#       Cancellation Policy
USER_WAIT_TO_CANCEL: float = min_to_sec(40)  # Time [sec] that a user waits before deciding to cancel an order
USER_CANCELLATION_PROBABILITY: float = 0.05  # Probability that a user will cancel an order if no courier is assigned

# Object Constants
ORDER_MAX_PICK_UP_SERVICE_TIME: int = min_to_sec(10)  # Maximum service time [sec] at the pick up location
ORDER_MAX_DROP_OFF_SERVICE_TIME: int = min_to_sec(5)  # Maximum service time [sec] at the drop off location
ORDER_MIN_SERVICE_TIME: int = min_to_sec(2)  # Minimum service time [sec] at either a pick up or drop off location
ORDER_TARGET_DROP_OFF_TIME: float = min_to_sec(40)  # Target time [sec] in which an order should be delivered
