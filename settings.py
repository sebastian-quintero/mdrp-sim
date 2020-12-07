from datetime import time
from typing import Dict, Any

from utils.datetime_utils import min_to_sec, hour_to_sec

DB_USERNAME: str = 'docker'  # DDBB Username
DB_PASSWORD: str = 'docker'  # DDBB Password
DB_HOST: str = '127.0.0.1'  # DDBB Host
DB_PORT: str = '5432'  # DDBB Port
DB_DATABASE: str = 'mdrp_sim'  # DDBB Name


class Settings:
    def __init__(self, attributes: Dict[str, Any] = None):
        self._attributes = attributes

    @property
    def attributes(self) -> Dict[str, Any]:
        return self._attributes

    def __getattr__(self, attr):
        return self._attributes.get(attr)


SIMULATION_KEYS = [
    'SIMULATE_FROM',
    'SIMULATE_UNTIL',
    'CREATE_USERS_FROM',
    'CREATE_USERS_UNTIL',
    'CREATE_COURIERS_FROM',
    'CREATE_COURIERS_UNTIL',
    'WARM_UP_TIME'
]

POLICIES_KEYS = [
    'DISPATCHER_CANCELLATION_POLICY',
    'DISPATCHER_BUFFERING_POLICY',
    'DISPATCHER_PREPOSITIONING_EVALUATION_POLICY',
    'DISPATCHER_PREPOSITIONING_POLICY',
    'DISPATCHER_MATCHING_POLICY',
    'COURIER_ACCEPTANCE_POLICY',
    'COURIER_MOVEMENT_EVALUATION_POLICY',
    'COURIER_MOVEMENT_POLICY',
    'USER_CANCELLATION_POLICY'
]

# Settings for the simulation
settings = Settings({
    # Project
    # --- List[int] = Desired instances to be simulated
    'INSTANCES': [3],
    # --- bool =  Enable / Disable specific (verbose) actor and policy logs
    'VERBOSE_LOGS': False,
    # --- Optional[Union[float, int]] = Seed for running the simulation. Can be None.
    'SEED': 8795,
    # str = Optimizer to use. Options: ['pulp', 'gurobi']
    'OPTIMIZER': 'pulp',

    # Simulation Constants
    # --- time =  Simulate from this time on
    'SIMULATE_FROM': time(0, 0, 0),
    # --- time =  Simulate until this time
    'SIMULATE_UNTIL': time(10, 0, 0),
    # --- time =  Create new users to submit orders from this time
    'CREATE_USERS_FROM': time(9, 0, 0),
    # --- time =  Create new users to submit orders until this time
    'CREATE_USERS_UNTIL': time(9, 5, 0),
    # --- time =  Create new couriers to log on from this time
    'CREATE_COURIERS_FROM': time(0, 0, 0),
    # --- time = Create new couriers to log on until this time
    'CREATE_COURIERS_UNTIL': time(0, 5, 0),
    # --- float = Warm up time [sec] to achieve steady state simulation
    'WARM_UP_TIME': hour_to_sec(3) + min_to_sec(0),

    # Simulation Policies - Dispatcher
    # --- str = Policy for canceling orders. Options: ['static']
    'DISPATCHER_CANCELLATION_POLICY': 'static',
    # --- str = Policy for buffering orders. Options: ['rolling_horizon']
    'DISPATCHER_BUFFERING_POLICY': 'rolling_horizon',
    # --- str = Policy for deciding when to evaluate prepositioning. Options: ['fixed']
    'DISPATCHER_PREPOSITIONING_EVALUATION_POLICY': 'fixed',
    # --- str = Policy for executing prepositioning. Options: ['naive']
    'DISPATCHER_PREPOSITIONING_POLICY': 'naive',
    # --- str = Policy for matching. Options: ['greedy', 'mdrp', 'mdrp_graph', 'mdrp_graph_prospects', 'modified_mdrp']
    'DISPATCHER_MATCHING_POLICY': 'mdrp',

    # Simulation Policies - Courier
    # --- str = Policy for accepting a notification. Options: ['uniform', 'absolute']
    'COURIER_ACCEPTANCE_POLICY': 'uniform',
    # --- str = Policy to determine if the courier wants to relocate. Options: ['neighbors', 'still']
    'COURIER_MOVEMENT_EVALUATION_POLICY': 'neighbors',
    # --- str = Policy that models the movement of a courier about the city. Options: ['osrm']
    'COURIER_MOVEMENT_POLICY': 'osrm',

    # Simulation Policies - User
    # --- str = Policy to decide if a user wants to cancel an order. Options: ['random']
    'USER_CANCELLATION_POLICY': 'random',

    # Simulation Policies Configuration - Dispatcher - Cancellation Policy
    # float = Time [sec] to cancel an order
    'DISPATCHER_WAIT_TO_CANCEL': min_to_sec(60),

    # Simulation Policies Configuration - Dispatcher - Buffering Policy
    # float = Time [sec] to buffer orders
    'DISPATCHER_ROLLING_HORIZON_TIME': min_to_sec(2),

    # Simulation Policies Configuration - Dispatcher - Prepositioning Evaluation Policy
    # float = Time [sec] to execute prepositioning
    'DISPATCHER_PREPOSITIONING_TIME': hour_to_sec(1),

    # Simulation Policies Configuration - Dispatcher - Matching Policy
    # float = Maximum distance [km] between a courier and a store
    'DISPATCHER_PROSPECTS_MAX_DISTANCE': 3,
    # int = Maximum number of orders a courier can carry simultaneously
    'DISPATCHER_PROSPECTS_MAX_ORDERS': 3,
    # float = Max offset time [sec] from a stop's expected timestamp
    'DISPATCHER_PROSPECTS_MAX_STOP_OFFSET': min_to_sec(10),
    # float = Time [sec] for ready route before avoiding stop offset
    'DISPATCHER_PROSPECTS_MAX_READY_TIME': min_to_sec(4),
    # int = Time [sec] to consider ready orders for target bundle size
    'DISPATCHER_MYOPIC_READY_TIME_SLACK': min_to_sec(10),
    # int = Precision to group orders into a proxy of stores
    'DISPATCHER_GEOHASH_PRECISION_GROUPING': 8,
    # float = Constant penalty for delays in the pick up of a bundle of orders
    'DISPATCHER_DELAY_PENALTY': 0.4,

    # Simulation Policies Configuration - Courier - Acceptance Policy
    # --- float = Minimum acceptance rate for any courier
    'COURIER_MIN_ACCEPTANCE_RATE': 0.4,
    # --- float = Time [sec] that a courier waits before accepting / rejecting a notification
    'COURIER_WAIT_TO_ACCEPT': 20,

    # Simulation Policies Configuration - Courier - Movement Evaluation Policy
    # float = Probability that a courier WILL move
    'COURIER_MOVEMENT_PROBABILITY': 0.4,
    #  float = Time [sec] that a courier waits before deciding to move
    'COURIER_WAIT_TO_MOVE': min_to_sec(45),

    # Simulation Policies Configuration - Courier - Other Constants
    # float = Money earned for dropping off an order
    'COURIER_EARNINGS_PER_ORDER': 3,
    # float = Rate at which the courier can be compensated per hour
    'COURIER_EARNINGS_PER_HOUR': 8,

    # Simulation Policies Configuration - User - Cancellation Policy
    # float = Time [sec] that a user waits before deciding to cancel an order
    'USER_WAIT_TO_CANCEL': min_to_sec(45),
    # float = Probability that a user will cancel an order if no courier is assigned
    'USER_CANCELLATION_PROBABILITY': 0.75,

    # Object Constants
    # int = Maximum service time [sec] at the pick up location
    'ORDER_MAX_PICK_UP_SERVICE_TIME': min_to_sec(10),
    # int =  Maximum service time [sec] at the drop off location
    'ORDER_MAX_DROP_OFF_SERVICE_TIME': min_to_sec(5),
    # int = Minimum service time [sec] at either a pick up or drop off location
    'ORDER_MIN_SERVICE_TIME': min_to_sec(2),
    # float = Target time [sec] in which an order should be delivered
    'ORDER_TARGET_DROP_OFF_TIME': min_to_sec(40),

})
