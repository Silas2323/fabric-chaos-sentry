"""First network-automation script: SSH to leaf1, run a show command, report pass/fail."""

import getpass

from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException

LEAF1 = {
    "device_type": "arista_eos",
    "host": "192.168.15.60",
    "username": "silas",
}


def check_leaf(device: dict, command: str) -> str:
    connection = ConnectHandler(**device)
    output = connection.send_command(command)
    connection.disconnect()
    return output


def main() -> None:
    device = dict(LEAF1)
    device["password"] = getpass.getpass(f"Password for {device['username']}@{device['host']}: ")

    try:
        output = check_leaf(device, "show version")
    except NetmikoAuthenticationException:
        print("FAIL: authentication rejected — check username/password")
        return
    except NetmikoTimeoutException:
        print("FAIL: no response — check IP, port 22, and reachability")
        return

    print(f"PASS: leaf1 ({device['host']}) reachable and authenticated")
    print("---- show version ----")
    print(output)


if __name__ == "__main__":
    main()
