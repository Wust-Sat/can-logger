# CAN Logger

First create virtual can interaface:

```shell
# Instal deps
sudo apt install can-utils iproute2

# Ensure the vcan module is loaded
sudo modprobe vcan

# Create a virtual CAN interface (e.g., vcan0) with CAN-FD enabled
sudo ip link add dev vcan0 type vcan
sudo ip link set vcan0 mtu 72 # Set MTU for CAN-FD (payload + header)
sudo ip link set vcan0 up # Bring the interface up

# Verify the interface
ip link show vcan0
```

Then you can run containers:

```shell
docker compose up --build
```