# Script to act as main node of network.

# Various imports
import threading
import json
import subprocess
import socket
import serial
import sys
import os
import traceback
import shutil
import argparse
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

current_datetime = datetime.today().strftime("%Y%m%d_%H%M%S")

@dataclass
class Data:
    message: str
    flag: bool

@dataclass
class Node:
    ip: str
    node_id: int
    distance: float
    angle_of_arrival: float

verbose = False
ip_table = []

def cmd(cmd_list: list, timeout: int = 5) -> str:
    """
    Executes a shell command
    
    ARGUMENT(S):
    cmd_str - str of command to be executed
    
    RETURNS:
    String containing output of cmd run
    """
    return subprocess.check_output(cmd_list, stderr=subprocess.PIPE, timeout=timeout).decode("utf-8")

def spawn_background_process(cmd_list: list):
    """
    Spawns a process running in the background.
    
    ARGUMENT(S):
    cmd_str - str containing command to execute.
    
    RETURNS
    Nothing.
    """
    subprocess.Popen(cmd_list, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

def sudo_process(cmd_list: list) -> str:
    """
    Some select processes require sudo to work properly. This simply spawns a process and feeds the password for sudo.
    
    ARGUMENT(S):
    cmd_str - command to execute.
    
    RETURNS:
    str containing command results.
    """
    proc = subprocess.Popen(cmd_list, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    proc.stdin.write("ODINnetwork321!\n")
    proc.stdin.flush()
    stdout,stderr = proc.communicate()

    return stdout,stderr


def create_log_dir(log_path: Path) -> Path:
    """
    Creates lof file directory
    
    ARGUMENT(S):
    log_path - path to send logs.
    
    RETURNS:
    Final path of log file(s)
    """
    if log_path.exists():
        cmd(["mkdir", "-p", f"{log_path}/uwb_network_logs"])
        log_path = log_path / f"/uwb_network_logs/network_node_run_{current_datetime}.txt"
    else:
        cmd(["mkdir", "-p", f"{log_path}"])
        if log_path.exists():
            cmd(["mkdir", "-p", f"{log_path}/uwb_network_logs"])
            log_path = log_path / f"/uwb_network_logs/network_node_run_{current_datetime}.txt"
        else:
            print("Failed to create log folder! Exiting...")
            exit(1)

    return log_path

def log_to_file(message: str, log_path: Path, debug: bool):
    """
    Logs messages to a file.
    
    ARGUMENT(S):
    log_path - path of log file.
    debug - option to determine if message is output to console.
    
    RETURNS:
    Nothing.
    """
    if debug:
        print(message)
    with open(log_path, "a") as a_file:
        a_file.write(f"{message}\n")

def communicate_to_edge_node(node_id: str, message: str) -> str:
    """
    Sends a message or command to an edge node.
    
    ARGUMENT(S):
    node_id - id of node on the network.
    message - message to send over available network interface.
    
    RETURNS:
    Response from node.
    """

def retrieve_uwb_serial_interface() -> str:
    """
    Retrieves the serial interface of the uwb kit connected.
    
    ARGUMENT(S):
    interface - interface passed in, simply returns this if not None.
    
    RETURNS:
    Serial interface of the uwb kit.
    """
    serial_interface = cmd(["sudo", "./get_qorvo_usb_interface.sh"])
    return serial_interface

def connect_to_node(node_id: str, log_path: Path):
    """
    Opens an active connection to a node in the network.
    
    """


def send_serial_command(interface: str, cmd_str: str): 
    """
    Sends a command to the UWB kit.
    
    ARGUMENT(S):
    interface - serial interface connected to UWB kit.
    cmd_str - str with command to send to UWB kit.
    
    RETURNS:
    Response from UWB kit.
    """
    with serial.Serial(port=interface, baudrate=115200, write_timeout=5) as serial_object:
        serial_object.write(f"{cmd_str}\r\n")
        serial_object.close()
        ret_val = serial_object.readline()

    return ret_val    

def read_serial_output(interface: str) -> str:
    """
    Reads a line from the serial interface of the UWB kit.
    
    ARGUMENT(S):
    interface - usb serial interface
    
    RETURNS:
    Line read from interface.
    """

    with serial.Serial(interface, baudrate=115200, timeout=5) as serial_obj:
        ret_val = serial_obj.readline()

    return ret_val

def main():
    """
    Main driver code
    """
    log_path = Path("/tmp")
    serial_interface = ""
    node_type = "edge"
    global verbose

    parser = argparse.ArgumentParser(description="Main node of UWB network.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Option to give more debug messages to the console.")
    parser.add_argument("-u", "--usb", help="Option to manually designate a serial device.")
    parser.add_argument("-d", "--dir", help="Option to choose log file location. Defaults to /tmp.")
    parser.add_argument("-n", "--nodetype", required=True, choices= ("edge", "main"), help="Determines which node type is being run. Defaults to edge node.")
    args = parser.parse_args()

    if args.nodetype:
        node_type = args.nodetype
    if args.verbose:
        verbose = True
    if args.usb:
        serial_interface = args.usb
    else:
        serial_interface = retrieve_uwb_serial_interface()
    if args.dir:
        log_path = create_log_dir(Path(args.dir))
    else:
        log_path = create_log_dir(log_path)
    
    # Start the UWB kit as an initiator or responder if a main node or edge node.
    if node_type =="edge":
        log_to_file("Starting edge node UWB ranging.", log_path, True)
        log_to_file("Sending command: respf", log_path, verbose)
        send_serial_command(serial_interface, "respf")
    else:
        log_to_file("Starting edge node UWB ranging.", log_path, True)
        log_to_file("Sending command: initf", log_path, verbose)
        send_serial_command(serial_interface, "initf")

if __name__ == "__main__":
    main()