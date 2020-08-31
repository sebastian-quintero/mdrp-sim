# mdrp-sim

This is a Meal Delivery Routing Problem Simulator (hence the name).
As such, it is a computational framework for solving the Meal Delivery Routing Problem. 
The computational framework consists of a simulated environment where different policies can be tested.
These policies consist of:

- Dispatching (assignment + routing) policies
- Movement (for couriers) policies
- Fleet allocation policies

A short explanation of this repo's directories can be found.
Please follow this short guide to get the project up and running.


## 1. Directories
This project is composed of the following directories:

```bash
.
├── instances
├── utils
├── README.md
└── requirements.txt

2 directories, 2 files
```

Let's dive into each directory.

### Instances
Here the different instances for testing out the `mdrp-sim` can be found. 
For each instance there are two files: `couriers.csv` and `order.csv`.
Each instance is a complete day of operation (12 a.m. to 11:59 p.m.) for a specific city.

The `couriers.csv` file contains information about all the couriers that came online for that day and contains the following columns:
- courier_id: an id to identify a courier.
- vehicle: mode of transportation. Can be: walking, bicycle, motorcycle or car.
- start_lat: latitude of the courier's position at the start of the shift.
- start_lng: longitude of the courier's position at the start of the shift.
- shift_starts_at: timestamp detailing when the courier started the shift.
- shift_ends_at: timestamp detailing when the courier ended the shift.

the `orders.csv` file contains information about all the orders processed during the day and contains the following columns:
- order_id: and id to identify an order.
- store_lat: latitude of the order's store's position.
- store_lng: longitude of the order's store's position.
- user_lat: latitude of the order's user's position.
- user_lng: longitude of the order's user's position.
- dispatch_at: timestamp detailing when should the order be dispatched.
- pickup_at_lb: timestamp detailing the lower bound of the pickup's time window.
- pickup_at_ub: timestamp detailing the upper bound of the pickup's time window.
- deliver_at_lb: timestamp detailing the lower bound of the delivery's time window.
- deliver_at_ub: timestamp detailing the upper bound of the delivery's time window.

### Utils
Project's utils can be found here. From logging to mathematical auxiliary functions.

## 2. Set up

### Python

It is highly recommended that [Anaconda](https://www.anaconda.com/) is used as the python distribution.
For python projects, it is recommended that a virtual environment is used to set things up.
After Anaconda is installed and correctly set up, please open a terminal console and stand in the root of the project. 

Let's create the environment with:

```bash
conda create -n mdrp-sim python=3.7
```

Now, let's activate said environment:
```bash
conda activate mdrp-sim
```

Make sure you are standing in the environment every time you are trying to run the project. The full env list can be seen using `conda env list`.

It is time to install the requirements used in the project. 
Let's install the open source libraries in a single step.
Run the following command :

```bash
pip install -r requirements.txt
```

If you have any trouble installing these libraries, be aware that the requirements are listed in the file `requirements.txt`.
Sometimes it's best to install problematic libraries by hand and omitting them from the `requirements.txt` file.
In such case run the following command:

```bash
pip install library_name
```

Let's use the directory's root as the python path, to avoid confusion of directory handling. 
Stand in the root of the `mdrp-sim` directory and execute the following command (Mac & Linux):

```bash
export PYTHONPATH=.
```

Cool! Python and the requirements are all set up!
