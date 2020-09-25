# mdrp-sim

This is a Meal Delivery Routing Problem Simulator (hence the name).
If you're in a hurry, check out:
- [Quick Setup](#quick-setup)
- [Quick Use](#quick-use)

If you have a bit more time on your hands, start reading from the [Intro](#intro) and work your way down. 

## Quick Setup
Let's do a lightning fast setup via terminal.

First, install [python](https://www.python.org/) ([Anaconda](https://www.anaconda.com/) distribution recommended) and [Docker](https://www.docker.com/get-started).
Stand in the root of this project.

Second, let's create a virtual environment for the project, install python requirements and make this the active python path.

```bash
conda create -n mdrp-sim python=3.7
conda activate mdrp-sim
pip install -r requirements.txt
export PYTHONPATH=.
```

Third, let's use docker to mount the Database.

```bash
docker pull postgres
docker run -p 5432:5432 --name mdrp-sim-db-container -e POSTGRES_USER='docker' -e POSTGRES_PASSWORD='docker' -e POSTGRES_DB='mdrp_sim' -d postgres
```

Fourth, in a separate terminal, let's use docker to mount the city routing ([OSRM](http://project-osrm.org/)) service (may take several minutes).

```bash
docker-compose up osrm_colombia
```

Let's confirm the docker stuff is correctly set up (use the original terminal) with:

```bash
docker ps
```

You should see something like this:

```bash
CONTAINER ID        IMAGE               COMMAND                  CREATED             STATUS              PORTS                    NAMES
218befee50e3        postgres            "docker-entrypoint.s…"   2 seconds ago       Up 2 seconds        0.0.0.0:5432->5432/tcp   mdrp-sim-db-container
edcc1aac43cb        colombia_osrm       "/bin/sh -c 'osrm-ro…"   3 days ago          Up 17 minutes       0.0.0.0:5000->5000/tcp   mdrp-sim_osrm_colombia_1
```

Fifth, set your project configurations in the `settings.py` file. 

Sixth, create the necessary tables in your DDBB and load the instance data into them (may take several minutes):

```bash
python3 ddbb/load_instances.py
```

If the terminal logs showed all instances were loaded to the DDBB and the connection was disposed, you're good to go.

## Quick Use

Stand in the root of the project.

Fire up a terminal and do:

````bash
docker-compose up
````

Leave this terminal alone and open up a new one.

Now, execute:

```bash
docker start mdrp-sim-db-container
```

To set the project's root as the `PYTHONPATH`, go ahead and type:

```bash
export PYTHONPATH=.
```

Finally, run the simulation with:

```bash
python3 simulate.py
```

Remember that all configurations for the simulation live in the `settings.py` file.


## Intro

This project is a computational framework for solving the Meal Delivery Routing Problem. 
The computational framework consists of a simulated environment.
Discrete events simulation is used and these are the most important definitions:

- Event: A sequence of items, facts, actions or changes triggered at a moment in time that follow a chronological order.
- Actor: Entity that makes decisions and executes actions (triggers events).
- Process: Current state of an actor. Can also be defined as a sequence of events during a specific time interval.
- Policy: Conditions and algorithms that describe how an actor makes a decision or executes an action.
- Object: Passive entity used to represent an abstract object, person or place. Doesn't make decisions or execute actions.

This framework allows for different policies to be tested, such as:

- Dispatching (assignment + routing) policies
- Movement (for couriers) policies
- Fleet allocation (prepositioning) policies

A short explanation of this repo's directories can be found.
A more extended guide to get the project up and running is provided.

## 1. Directories
This project is composed of the following directories:

```bash
.
├── actors
├── ddbb
├── docker
├── instances
├── objects
├── policies
├── services
├── tests
├── utils
├── README.md
├── alembic.ini
├── docker-compose.yml
├── requirements.txt
├── settings.py
└── simulate.py

9 directories, 6 files
```

Let's dive into each directory.

### Actors
Here you can find the classes that handle the MDRP's actors states and events:

- Courier
- Dispatcher
- User

### DataBase (DDBB)
All scripts and migrations necessary for the DDBB to work live here.

### Docker
Files for managing docker stuff.

### Instances
Here the different instances for testing out the `mdrp-sim` can be found. 
For each instance there are two files: `couriers.csv` and `order.csv`.
Each instance is a complete day of operation (12 a.m. to 11:59 p.m.) for a specific city.

The `couriers.csv` file contains information about all the couriers that came online for that day and contains the following columns:
- courier_id: an id to identify a courier.
- vehicle: mode of transportation. Can be: walking, bicycle, motorcycle or car.
- on_lat: latitude of the courier's position at the start of the shift.
- on_lng: longitude of the courier's position at the start of the shift.
- on_time: timestamp detailing when the courier started the shift.
- off_time: timestamp detailing when the courier ended the shift.

the `orders.csv` file contains information about all the orders processed during the day and contains the following columns:
- order_id: and id to identify an order.
- pick_up_lat: latitude of the order's pick_up location.
- pick_up_lng: longitude of the order's pick_up location.
- drop_off_lat: latitude of the order's drop_off location.
- drop_off_lng: longitude of the order's drop_off location.
- placement_time: timestamp detailing the order's creation time.
- preparation_time: timestamp detailing when the order starts being prepared.
- ready_time: timestamp detailing when the order is ready to be picked up.
- expected_drop_off_time: timestamp detailing when the order should be dropped off.

### Objects
The different class objects used for the MDRP can be found here, such as:

- Order
- Route
- Vehicle
- ...

### Policies
Interchangeable policies used by the actors can be found here. 
A policy dictates the logic and actions that must be executed by an actor after some event.
Some of the policies are:

- Movement policy for the Courier
- Cancellation policy for the Dispatcher
- Acceptance policy for the Courier
- ...

### Services
Services for the simulator, such as the city routing service (OSRM) and the optimization service can be found here.
These services may be used by policies or actors in different ways.

### Tests
Suite of unit testing the code

### Utils
Project's utils can be found here. From logging to mathematical auxiliary functions.

## 2. Set up

This section is an extension of the [Quick Setup](#quick-setup) section. 
Please take your time to correctly set up the project.

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

### Docker
Please make sure you have [Docker](https://www.docker.com/get-started) installed.
Docker will be used to manage the Database (postgresql) and the [OSRM](http://project-osrm.org/) service.

### Open Source Routing Machine
To have a OSRM that delivers city routes mounted in your local environment, we will mount it via Docker.
All the instances herein contained belong to the country Colombia. As such, we will:

1. Download the [OpenStreetMap](https://www.openstreetmap.org/#map=6/4.632/-74.299) graph for Colombia from [Geofabrik](https://www.geofabrik.de/geofabrik/).
1. Use a bounding box to use the part of the country that is useful for the instances and extract it with [osmcode.org](https://osmcode.org/).
1. Extract the car profile for the map.
1. Mount a web server on port 5000 with `osrm-routed` using the Contraction Hierarchies (CH) algorithm.
1. Listen for requests and return the route for a lat, lng origin and destination.

To accomplish all of this, stand in the root of the project and run the following command:

```bash
docker-compose up osrm_colombia
```

This process may take several minutes to complete. When it's done, you should see something like this:

```bash
Starting mdrp-sim_osrm_colombia_1 ... done
Attaching to mdrp-sim_osrm_colombia_1
osrm_colombia_1  | [info] starting up engines, v5.22.0
osrm_colombia_1  | [info] Threads: 8
osrm_colombia_1  | [info] IP address: 0.0.0.0
osrm_colombia_1  | [info] IP port: 5000
osrm_colombia_1  | [info] http 1.1 compression handled by zlib version 1.2.8
osrm_colombia_1  | [info] Listening on: 0.0.0.0:5000
osrm_colombia_1  | [info] running and waiting for requests
```

To stop the server you may use `ctrl+c`. 
Next time the server starts, it will do so immediately since all the data is ready.
At any time you may check if the container is running using this command in a different terminal: 

```bash
docker ps
```

You should see something like this:

```bash
CONTAINER ID        IMAGE               COMMAND                  CREATED             STATUS              PORTS                    NAMES
edcc1aac43cb        colombia_osrm       "/bin/sh -c 'osrm-ro…"   3 days ago          Up 2 minutes        0.0.0.0:5000->5000/tcp   mdrp-sim_osrm_colombia_1
```

If the container is running then cool! OSRM is all set up.

### Postgresql

This project saves the information in a postgresql relational data base.
It is recommended that Docker is used to handle the DDBB.

Let's start by pulling the latest postgresql image:

```bash
docker pull postgres
```

Let's build the container and name it `mdrp-sim-db-container`:

```bash
docker run -p 5432:5432 --name mdrp-sim-db-container -e POSTGRES_USER='docker' -e POSTGRES_PASSWORD='docker' -e POSTGRES_DB='mdrp_sim' -d postgres
```

Data will be stored in the DDBB each time the service is run. 
Note that the DDBB has a user and a password (both are `docker`). 
The name of the DDBB is set to `mdrp_sim`.

Let's check if the postgresql container is running correctly with:

```bash
docker ps
``` 

You should see something similar to:

```bash
CONTAINER ID        IMAGE               COMMAND                  CREATED             STATUS              PORTS                    NAMES
a32029bf4010        postgres            "docker-entrypoint.s…"   7 months ago        Up 1 second         0.0.0.0:5432->5432/tcp   mdrp-sim-db-container
```

If the container is running, cool! Postgresql is all set up!

#### Migrations

To interact with the DDBB for adding/removing schemas, tables and columns, a migration must be performed.

First of all, let's make sure the `PYTHONPATH` is set correctly. Stand at the root of the project and run:

```bash
export PYTHONPATH=.
```

To check the current migrations you can run:

```bash
alembic history
```

To execute migrations manually you can run:

```bash
alembic upgrade head
```

To create a new migration automatically, you can run:

```bash
alembic revision --autogenerate -m "<migration_message>"
```

With this last command, a new file should've been generated at `./ddbb/versions/`.