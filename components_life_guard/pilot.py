import can

bus = can.interface.Bus(channel="vcan0", bustype="socketcan", fd=True)


#### from life_center -> LifeGuard
def send_state_change(node_id: int, target_state: str):
    state_commands = {"start": 0x01, "stop": 0x02, "pre-op": 0x80, "reset": 0x81}

    msg = can.Message(
        arbitration_id=0x10000000,
        data=[state_commands[target_state], node_id],
        is_fd=True,
        dlc=2,
    )
    bus.send(msg)


while 1:
    line = input("Imput: ").split()
    if len(line) != 2:
        print("Too few arguments")
        arg1 = None
        arg2 = None
    else:
        arg1, arg2 = line

    if not (arg1 == "start" or arg1 == "stop" or arg1 == "reset" or arg1 == "pre-op"):
        arg1 = None

    if arg1 != None and arg2 != None:
        send_state_change(int(arg2), arg1)
