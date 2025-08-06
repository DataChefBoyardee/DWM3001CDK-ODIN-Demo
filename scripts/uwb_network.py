# Script to act as main node of network.

# Important imports
import threading
import json
import socket
import time
import subprocess
import socket
import serial
import sys
import traceback
import argparse
from enum import Enum
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from typing import Union

thread_status = Enum('Thread_Status', 'Not_Run Success Error Exception Undefined')

# Globals to be used throughout the script.
current_datetime = datetime.today().strftime("%Y%m%d_%H%M%S")
exit_script = False
serial_lock = threading.Condition()
log_file_write_lock = threading.Condition()
results_list = []
node_distances = []
node_corrected_distances = []
node_ips = []
node_ips_addr = []

@dataclass
class Thread_Pair:
    threads: tuple

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
        cmd(["mkdir", "-p", f"{log_path}/uwb_network_logs/network_node_run_{current_datetime}"])
        log_path = log_path / f"{log_path}/uwb_network_logs/network_node_run_{current_datetime}"
    else:
        cmd(["mkdir", "-p", f"{log_path}"])
        if log_path.exists():
            cmd(["mkdir", "-p", f"{log_path}/uwb_network_logs"])
            cmd(["mkdir", "-p", f"{log_path}/uwb_network_logs/network_node_run_{current_datetime}"])
            log_path = log_path / f"{log_path}/uwb_network_logs/network_node_run_{current_datetime}"
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
    with open(log_path, "a+") as a_file:
        a_file.write(f"{message}\n")

def connect_to_edge_node(node_ip: str, index: int) -> str:
    """
    Establishes a connection to an edge node and sends distance data to it.
    
    ARGUMENT(S):
    node_ip - ip of node on the network.
    index - index of thread results to pull from.
    
    RETURNS:
    Response from node.
    """
    send_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    send_socket.bind(node_ip, 5001)
    return



def retrieve_uwb_serial_interface() -> str:
    """
    Retrieves the serial interface of the uwb kit connected.
    
    ARGUMENT(S):
    interface - interface passed in, simply returns this if not None.
    
    RETURNS:
    Serial interface of the uwb kit.
    """
    serial_interface = cmd(["sudo", "./get_qorvo_usb_interface.sh"])
    return serial_interface.strip("\n")

def listen_for_nodes(log_file: Path):
    """
    Listens on a predefined port for open node connections.
    """
    global node_ips
    global exit_script
    global node_ips_addr
    server_socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('',5000))

    while not exit_script:
        if not is_socket_closed(server_socket, log_file):
            data, (ip, port) = server_socket.recvfrom(1024, socket.MSG_DONTWAIT)
            log_file_write_lock.acquire()
            log_to_file(f"Received IP {ip}", log_file, False)
            log_file_write_lock.notify()
            log_file_write_lock.release()
            if ip not in node_ips:
                node_ips.append(ip)
                node_ips_addr.append((ip, len(node_ips)))
            msg = f"Received. Addr:{len(node_ips)}"
            server_socket.sendto(msg,(ip, 5001))

def is_socket_closed(sock: socket.socket, log_file: Path) -> bool:
    try:
        # this will try to read bytes without blocking and also without removing them from buffer (peek only)
        data = sock.recv(16, socket.MSG_DONTWAIT | socket.MSG_PEEK)
        if len(data) == 0:
            return True
    except BlockingIOError:
        return False  # socket is open and reading from it would block
    except ConnectionResetError:
        return True  # socket was closed for some other reason
    except Exception as e:
        log_file_write_lock.acquire()
        log_to_file("unexpected exception when checking if a socket is closed", log_file, False)
        log_file_write_lock.notify()
        log_file_write_lock.release()
        return False
    return False

def send_serial_command(interface: str, cmd_str: str, log_file: Path): 
    """
    Sends a command to the UWB kit.
    
    ARGUMENT(S):
    interface - serial interface connected to UWB kit.
    cmd_str - str with command to send to UWB kit.
    
    RETURNS:
    Response from UWB kit.
    """
    msg = str.encode(f"{cmd_str}\r\n")
    with serial.Serial(port=interface, baudrate=115200, write_timeout=5) as serial_object:
        serial_object.flushInput()
        serial_object.flushOutput()
        time.sleep(1)
        serial_object.write(msg)
        ret_val = serial_object.readline().decode("utf-8")
        log_to_file(f"Serial response: {ret_val}", log_file, True)
        serial_object.close()

    return ret_val    

def listen_serial_output(interface: str, log_file: str) -> str:
    """
    Listens to serial output and updates variable with measurements.
    
    ARGUMENT(S):
    interface - usb serial interface
    
    RETURNS:
    Nothing.
    """
    global exit_script
    while not exit_script:
        with serial.Serial(interface, baudrate=115200, timeout=0.25) as serial_obj:
            serial_obj.flushInput()
            serial_obj.flushOutput()
            time.sleep(0.1)
            line = serial_obj.readline().decode("utf-8")
            try:
                line = json.loads(line)
            except Exception as e:
                continue
            log_to_file(line['results'][0]['D_cm'], log_file, True)
            log_to_file(line['results'][0]['Addr'], log_file, True)
            serial_obj.close()

def start_uwb_node(interface: str, node_type: str, log_file: Path) -> list:
    """
    Starts this node of the network.
    
    ARGUMENT(S):
    interface - serial interface of UWB kit.
    node_type - type of node being started.
    log_path - path to log file.
    
    RETURNS:
    Results list pulled from node threads.
    """
    serial_output_log = log_file / f"uwb_serial_output_{current_datetime}.txt"
    main_log = log_file / f"main_node_run_{current_datetime}.txt"

    # Start the node based on node_type passed in.
    if node_type =="edge":
        edge_node_thread(interface, log_file)
    else:
        main_node_thread(interface, log_file)

def main_node_thread(interface: str, log_file: Path) -> list:
    """
    Main node thread logic
    
    ARGUMENT(S):
    interface - serial interface of UWB kit.
    log_file - log file where output is kept.
    edge_nodes - number of edge nodes connected.
    
    RETURNS:
    List of general results from threads.
    """
    global results_list
    global exit_script
    uwb_init_cmd = "initf "
    main_log = log_file / f"main_node_run_{current_datetime}.txt"
    serial_output_log = log_file / f"uwb_serial_output_{current_datetime}.txt"
    distances_log = log_file / f"module_distances_{current_datetime}.txt"
    node_ip_cur_len = 0

    # Spend some time initially listening for active node connections.
    log_to_file("Listening for active node connections.", main_log, True)
    listening_thread = threading.Thread(target=listen_for_nodes, args=[main_log,])
    listening_thread.start()
    time.sleep(5)
    
    # Assign addresses to ip's and start initiator.
    log_to_file("Starting edge node UWB ranging.", main_log, True)
    if node_ips > 1:
        uwb_init_cmd = "initf 4 2400 200 25 2 42 01:02:03:04:05:06:07:08 1 0 0 "
        for i in range(1, len(node_ips)):
            uwb_init_cmd += f"{i} "
    log_to_file(f"Sending command: {uwb_init_cmd}", serial_output_log, verbose)
    send_serial_command(interface, f"{uwb_init_cmd}", serial_output_log)

    # Start UWB kit listener.
    serial_thread = threading.Thread(target=listen_serial_output, args=[interface,serial_output_log,])
    serial_thread.start()

    # Prepare individual connection threads.
    log_to_file("Starting distance data gathering.",main_log,True)
    node_ip_cur_len = len(node_ips)
    threads = [None] * node_ip_cur_len
    results_list = [thread_status.Not_Run] * node_ip_cur_len
    node_distances = [None] * node_ip_cur_len
    for i in range(len(threads)):
        threads[i] = threading.Thread(target=connect_to_edge_node, args=[node_ips[i],i])
        threads[i].start()

    # Start thread to listen for user input to quit script.
    user_input_thread = threading.Thread(target=listen_for_user_input)
    user_input_thread.start()

    # Output updating distances, and add new nodes as they connect.
    while not exit_script:
        if node_ip_cur_len < len(node_ips):
            for i in range(node_ip_cur_len, len(node_ips)):
                results_list.append(thread_status.Not_Run)
                threads.append(threading.Thread(target=connect_to_edge_node, args=[node_ips[i],i]))
                threads[i].start()
            node_ip_cur_len = len(node_ips)
        for i in range(len(node_distances)):
            log_to_file(f"Node {i}: {node_distances[i]}"), distances_log, True
#        log_to_file("\n", distances_log, False)
#        print("Press \"q\" to quit.")
#        sys.stdout.flush()

    # Join threads then exit.
    user_input_thread.join()
    listening_thread.join()
    serial_thread.join()
    for i in range(len(threads)):
        threads[i].join()

def listen_for_user_input():
    """
    Simple method for listening for user input in the background. Meant to be threaded.
    """
    global exit_script
    while True:
        user_input = input()
        if user_input == "q":
            print("Quiting!")
            exit_script = True
            break

def edge_node_thread(interface: str, log_file: Path):
    """
    Edge node thread logic
    
    ARGUMENT(S):
    interface - serial interface of UWB kit.
    log_file - log file where output is kept.
    
    RETURNS:
    Nothing.
    """
    global results_list
    global exit_script
    main_log = log_file / f"main_node_run_{current_datetime}.txt"
    serial_output_log = log_file / f"uwb_serial_output_{current_datetime}.txt"
    distances_log = log_file / f"module_distances_{current_datetime}.txt"

    server_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    server_socket.bind(('',5001))
    data, (ip, port) = server_socket.recvfrom(1024)
    str_split = str(data).split(":")
    addr = str_split[1]

    log_to_file("Starting edge node UWB ranging.", main_log, True)
    log_to_file(f"Sending command: respf 4 2400 200 25 2 42 01:02:03:04:05:06:07:08 1 0 0 {addr}", serial_output_log, verbose)
    send_serial_command(interface, f"respf 4 2400 200 25 2 42 01:02:03:04:05:06:07:08 1 0 0 {addr}", serial_output_log)
    edge_node_thread(interface, log_file)

    # Start UWB kit listener.
    serial_thread = threading.Thread(target=listen_serial_output, args=[interface,serial_output_log,])
    serial_thread.start()

    # Start thread to listen for user input to quit script.
    user_input_thread = threading.Thread(target=listen_for_user_input)
    user_input_thread.start()

    while not exit_script:
        data, (ip, port) = server_socket.recvfrom(1024)
        log_file_write_lock.acquire()
        log_to_file(f"Received IP {ip}", log_file, False)
        log_file_write_lock.notify()
        log_file_write_lock.release()

def get_uwb_kit_info(log_file: Path):
    """
    Grabs version info from UWB kit.
    """

def main():
    """
    Main driver code
    """
    log_path = Path("/tmp")
    serial_interface = ""
    node_type = "edge"
    global verbose
    global results_list

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
    start_uwb_node(serial_interface, node_type, log_path)


if __name__ == "__main__":
    main()
