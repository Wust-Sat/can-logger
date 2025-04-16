#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

# echo "Ensuring vcan module is loaded..."
# modprobe vcan

echo "Setting up vcan0 interface..."
# Try to add the device, ignore error if it already exists
ip link add dev vcan0 type vcan || true
# Ensure the interface is up
ip link set up vcan0

echo "vcan0 setup complete. Executing command: $@"
# Execute the command passed to the container (from docker-compose CMD/command)
exec "$@"
