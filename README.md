# CAN Logger

**CAN Logger** is a tool for listening to and logging CAN/CAN-FD frames into an SQLite database. It allows easy monitoring of CAN bus traffic, message analysis, and later filtering and browsing of recorded messages.

## How it works

- The program listens on a selected CAN interface (e.g., `vcan0`, `can0`) and displays received frames in a readable format.
- Each received message is saved to an SQLite database (`can_messages.db` by default or as specified by the user).
- You can filter and browse saved messages using tools from the `can_logger/database_tools` directory (e.g., by date, arbitration ID, or last N messages).

## Quick start

First, create a virtual CAN interface:

```shell
# Install dependencies
sudo apt install can-utils iproute2

# Load the vcan module
sudo modprobe vcan

# Create a virtual CAN-FD interface
sudo ip link add dev vcan0 type vcan
sudo ip link set vcan0 mtu 72 # Set MTU for CAN-FD
sudo ip link set vcan0 up

# Verify the interface
ip link show vcan0
```

Then you can run the containers:

```shell
docker compose up --build
```

## Running the logger manually

You can run the logger directly with Python:

```shell
python3 -m can_logger.sniffer -i vcan0
```

or using the asynchronous version:

```shell
python3 -m can_logger --interface vcan0
```

## Browsing the database

To browse and filter saved messages, use:

```shell
python3 -m can_logger.database_tools --mode all
python3 -m can_logger.database_tools --mode last -n 20
python3 -m can_logger.database_tools --mode id --arbitration-id 123
python3 -m can_logger.database_tools --mode date --date 2024-06-03
```

## Features

- CAN/CAN-FD listening and logging to SQLite database
- Support for various message filtering modes
- Easy to run in a Docker container or locally
- Simple CLI interface based on [Click](https://click.palletsprojects.com/)

---

For more information, see the source code and the `can_logger/database_tools` directory.