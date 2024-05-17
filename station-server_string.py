import multiprocessing
import socket
import csv
import json
import time
from datetime import datetime
import copy
import os
import ast
import subprocess

# Harrison Harun | 23347644
# Aarif Lamat | 23628374
# Enrico Tionandra | 23732436
# Nicholas Mulyawan | 23044774

class NetworkServer(multiprocessing.Process):
    def __init__(self, station_name, browser_port, query_port, adjacent_addrs):
        super().__init__()
        self.station_name = station_name
        self.browser_port = int(browser_port)
        self.query_port = int(query_port)
        self.adjacent_addresses = adjacent_addrs
        self.adjacent_ips = [addr.split(':')[0] for addr in self.adjacent_addresses]
        self.adjacent_ports = [int(addr.split(':')[1]) for addr in self.adjacent_addresses]
        #### change this to ur pc's IP address. To find ur IP address in Linux type "ifconfig" in ur terminal, if on windows type "ipconfig" on cmd/powershell
        # self.host_ip = "127.0.0.1"
        # Aarif's on Unifi
        # self.host_ip = "10.135.223.145"
        ### Aarif's on hotspot ###
        # self.host_ip = "172.20.10.2"
        ### Nico's on Unifi
        #self.host_ip = "10.135.102.29"
        # My Hotspot
        # self.host_ip = "172.20.10.4"
        ####
        self.host_ip = self.get_your_ip()
        self.timetable_filename = f"tt-{self.station_name}"
        self.timetable = None
        self.station_list = []
        self.station_list_queue = multiprocessing.Queue()  # Queue for station list updates
        self.journey_list_queue = multiprocessing.Queue()
        self.destination = None
        self.journey = [["odyssey", query_port, "destination"], [station_name], [query_port]] 
        self.journey_list = []
        self.temp_list = []
        self.hard_temp = []
        self.start_time = "9:00"
        self.visited = [station_name]
        self.counter = 0
        self.last_modified_time = 0

    def get_your_ip(self):
        try:
            result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
            ip_address = result.stdout.strip()
            print(f"+++ IP Address: {ip_address} +++")
            return ip_address
        except subprocess.CalledProcessError as e:
            print(f"An error occurred: {e}")
        return None

    def run(self):
        # Load timetable
        self.load_timetable()
        self.last_modified_time = os.stat(self.timetable_filename).st_mtime

        # Initialize TCP server
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_socket.bind((self.host_ip, self.browser_port))
        self.tcp_socket.listen(5)

        # Initialize UDP socket
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind((self.host_ip, self.query_port))

        print(f"Station Server '{self.station_name}' started. TCP Port: {self.browser_port}, UDP Port: {self.query_port}, Neighbours (IP:UDP Port): {self.adjacent_addresses}")
        
        # Start UDP handler
        udp_handler = multiprocessing.Process(target=self.handle_udp)
        udp_handler.start()
        print(f"station list: {self.station_list}")


        # Ping adjacent ports for their station name and port number
        while len(self.station_list) != len(self.adjacent_ports):
            query_data = "query_station"

            # for port in self.adjacent_ports:
            for addr in self.adjacent_addresses:
                neighboring_station_address = (addr.split(":")[0], int(addr.split(":")[1]))
                self.udp_socket.sendto(query_data.encode("utf-8"), neighboring_station_address)
                time.sleep(1)


            if not self.station_list_queue.empty():
                self.station_list = self.station_list_queue.get()
            # print("STILL GOING!!!")
            print(f"station list: {self.station_list}")
                
        
        try:
            tcp_handler = multiprocessing.Process(target=self.handle_tcp)
            tcp_handler.start()
            while True:
                # Check for timetable file changes
                current_modified_time = os.stat(self.timetable_filename).st_mtime
                # print("EXDEEDEE")
                #print(f"1: {current_modified_time}")
                #print(f"2: {self.last_modified_time}")
                if current_modified_time != self.last_modified_time:
                    print("WAHOO")
                    # Timetable file has changed
                    self.last_modified_time = current_modified_time
                    self.load_timetable()
                    print("Timetable updated")
                
                time.sleep(1)  # Check every 1 second for changes
        except KeyboardInterrupt:
            pass
        finally:
            self.tcp_socket.close()
            self.udp_socket.close()
        
    def handle_tcp(self):
        try:
            while True:
                tcp_conn, _ = self.tcp_socket.accept()
                # START TIMER HERE
                request_data = tcp_conn.recv(4096).decode("utf-8")
                if request_data:
                    http_method, http_path, _ = request_data.split(" ", 2)
                    if http_method == "GET" and http_path.startswith("/?to="):
                        self.visited = [self.station_name]
                        self.destination = http_path.split("=")[1]
                        self.journey[0][2] = self.destination
                        self.hard_temp = copy.deepcopy(self.journey)
                        journey_list = []

                        
                        # Start linear search of the time from the timetable from the 4th item [arrival-time, arrival-station]
                        for sublist in self.timetable[3:]:
                            time_in_sublist = sublist[0]  # set time
                            # Convert string time to datetime objects
                            time_in_timetable_datetime = datetime.strptime(time_in_sublist, "%H:%M")
                            start_time_datetime = datetime.strptime(self.start_time, "%H:%M")
                            if time_in_timetable_datetime >= start_time_datetime: # Compare time
                                for station in self.visited: # check for past station visited.
                                    if sublist[-1] == station:
                                        self.counter += 1
                                if self.counter > 0: # If more than 0, it means the station has been visited before, resets counter
                                    self.counter = 0
                                    continue         # if you have visited this station before (gone to this station at an earlier time), go to the next [arrival-time, arrival-station] route
                                else:
                                    print(f"Time found: {time_in_sublist}")
                                    self.journey.append(sublist) # add schedule to the end of the journey list
                                    self.journey[1].append(sublist[-1]) # add arrival station to the stations visited list
                                    self.counter = 0
                                    if self.journey[-1][-1] == self.journey[0][2]: # Compare latest journey, end journey if match
                                        self.journey[0].append("ended")
                                        self.journey_list.append(self.journey)
                                        print("Instant Journey's end")
                                        print(self.journey_list)
                                        journey_list.append(self.journey)
                                        self.journey = self.hard_temp
                                        break   # end the search for a path to the destination
                                    else:
                                        for port in self.station_list:
                                            station_name = port[0]
                                            port_number = port[1]
                                            if station_name == self.journey[-1][-1]:
                                                print(f"{self.station_list}")
                                                print(f"station name: {station_name}")
                                                print(f"{self.journey[-1][-1]}")
                                                journey_data = self.journey
                                                # find corresponding ip to the port_number
                                                adj_ip = ""
                                                for address in self.adjacent_addresses:
                                                    if int(address.split(':')[1]) == port_number:
                                                        adj_ip = address.split(":")[0]
                                                adjacent_addr = (adj_ip, port_number)
                                                # json
                                                ### CONVERT LIST TO STRING FOR COMMUNICATING BETWEEN SERVERS ###
                                                journey_data_str = '|'.join([str(item) for item in self.journey])
                                                self.udp_socket.sendto(journey_data_str.encode("utf-8"), adjacent_addr)
                                                self.visited.append(station_name)
                                                print(f"{journey_data}")
                                                print(f"sent journey data to {adjacent_addr}")
                                                self.journey = self.hard_temp

                        print("end of timetable")
                        while len(journey_list) < 1:
                            time.sleep(5)
                            while not self.journey_list_queue.empty():
                                journey_list.append(self.journey_list_queue.get())
                                
                        #print(f"final Journeys End: {journey_list}")
                        
                        # If more than one journey returned, find the fastest journey, taking into account midnights
                        if len(journey_list) > 1:
                            print("more than 1 detected")
                            valid = []
                            for journ in journey_list:
                                if journ[0][0][-1] == "midnight":
                                    continue
                                else:
                                    valid.append(journ)
                                    
                            if valid == []:
                                # All journey returned are past midnight
                                journey_list = []
                            else:
                                endtime = valid[0][0][-1][3]
                                shortest = valid[0]
                                for journey in valid:
                                    duration = journey[0][-1][3]
                                    print(f"duration: {duration}")
                                    print(f"endtime: {endtime}")
                                    if datetime.strptime(duration, "%H:%M") < datetime.strptime(endtime, "%H:%M"):
                                        endtime = duration
                                        shortest = journey
                                        
                                    else:
                                        continue
                                journey_list = shortest
                        
                        if journey_list[0][0][-1] == "midnight":
                            journey_list = []

                        # Handle TCP request
                        response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: Closed\r\n\r\n"
                        response += f"<html><body><h1>Journey from {self.station_name} to {self.destination} at {self.start_time}</h1>\n"
                        
                        #print(f"{self.journey_list}")
                        if journey_list == []:
                            response += f"<p>there is no journey from {self.station_name} to {self.destination} leaving after {self.start_time} today</p>"
                        else:
                            for steps in journey_list[0][3:]:
                                response += f"<p>Catch {steps[1]} from {steps[2]}, at time {steps[0]}, to arrive at {steps[4]} at time {steps[3]}.</p>\n"
                            
                        #response += f"<p>Final Journey's End: {journey_list}</p>"
                        response += "</body></html>"
                        tcp_conn.sendall(response.encode("utf-8"))
                        journey_list = []
                        
                        while not self.journey_list_queue.empty():
                            self.journey_list_queue.get()                        

                    else:
                        response = "HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\nConnection: Closed\r\n\r\n"
                        response += "<html><body><h1>404 Not Found</h1></body></html>"
                        tcp_conn.sendall(response.encode("utf-8"))
                    tcp_conn.close()
        except KeyboardInterrupt:
            pass

    def handle_udp(self):
        try:
            while True:
                data, addr = self.udp_socket.recvfrom(4096)
                if "query_station" in data.decode("utf-8"):
                    # station_data = [self.station_name, self.query_port, "station_port"]
                    station_data_string = self.station_name + "," + str(self.query_port) + "," + "station_port"
                    # station_json = json.dumps(station_data)
                    self.udp_socket.sendto(station_data_string.encode("utf-8"), addr)
                    print(f"sent station data to {addr}")
                elif "station_port" in data.decode("utf-8"):
                    station_list = data.decode("utf-8").split(",")
                    if self.station_list:
                        for item in self.station_list:
                            if item[1] == station_list[1]:
                                break
                        else:
                            self.station_list.append(station_list)
                            self.station_list_queue.put(self.station_list)
                    else:
                        self.station_list.append(station_list)
                        self.station_list_queue.put(self.station_list)  # Put updated station list into queue for synchronization
                elif "odyssey" in data.decode("utf-8"):
                    
                    if "ended" in data.decode("utf-8") or "midnight" in data.decode("utf-8"):
                    
                        # journey_list = json.loads(data.decode("utf-8"))
                        # Split the string by '|'
                        split_strings = data.decode("utf-8").split('|')

                        # Convert each split string back to its list format
                        journey_list = [ast.literal_eval(item) for item in split_strings]
                        if len(journey_list[2]) > 1:
                            journey_list[2].pop(-1)
                            port_number = int(journey_list[2][-1])
                            # journey_data = journey_list
                            journey_data_str = '|'.join([str(item) for item in journey_list])
                            adj_ip = ""
                            for address in self.adjacent_addresses:
                                if int(address.split(':')[1]) == port_number:
                                    adj_ip = address.split(":")[0]
                            adjacent_addr = (adj_ip, port_number)
                            self.udp_socket.sendto(journey_data_str.encode("utf-8"), adjacent_addr)
                        else:
                            print("end pinged")
                            self.journey_list = []
                            self.journey_list.append(journey_list)
                            self.journey_list_queue.put(self.journey_list)
                            print(self.journey_list)
                        
                    else:
                        # self.temp_list = json.loads(data.decode("utf-8"))
                        # Split the string by '|'
                        split_strings = data.decode("utf-8").split('|')

                        # Convert each split string back to its list format
                        self.temp_list = [ast.literal_eval(item) for item in split_strings]
                        self.journey = copy.deepcopy(self.temp_list)
                        self.visited = self.temp_list[1]
                        midnight = 0
                        for sublist in self.timetable[3:]:
                            time_in_sublist = sublist[0]  # set time
                            time_in_timetable_datetime = datetime.strptime(time_in_sublist, "%H:%M")
                            latest_time_datetime = datetime.strptime(self.temp_list[-1][3], "%H:%M")
                            if time_in_timetable_datetime >= latest_time_datetime: # Compare time
                                midnight += 1
                                for station in self.visited: #check for past station visited.
                                    if sublist[-1] == station:
                                        self.counter += 1
                                if self.counter > 0:
                                    self.counter = 0
                                    continue
                                else:
                                    print(f"time found: {time_in_timetable_datetime}")
                                    self.temp_list.append(sublist)
                                    self.temp_list[1].append(sublist[-1])
                                    self.counter = 0
                                    if self.temp_list[-1][-1] == self.temp_list[0][2]: # Compare latest journey, end journey if match
                                        self.temp_list[0].append("ended")
                                        print(f"journey ended {self.temp_list[-1][-1]}")
                                        print(f"journey ended {self.temp_list[0][2]}")
                                        # journey_data = self.temp_list
                                        port_number = int(self.temp_list[2][-1])
                                        adj_ip = ""
                                        for address in self.adjacent_addresses:
                                            if int(address.split(':')[1]) == port_number:
                                                adj_ip = address.split(":")[0]
                                        adjacent_addr = (adj_ip, port_number)
                                        journey_data_str = '|'.join([str(item) for item in self.temp_list])
                                        # self.udp_socket.sendto(json.dumps(journey_data).encode("utf-8"), adjacent_addr)
                                        self.udp_socket.sendto(journey_data_str.encode("utf-8"), adjacent_addr)
                                        self.visited.append(self.temp_list[-1][-1])
                                        self.temp_list = self.journey
                                        print(f"sent final {journey_data_str} to {adjacent_addr}")
                                    else:
                                        for port in self.station_list:
                                            station_name = port[0]
                                            port_number = port[1]
                                            print(f"attempt to send {self.temp_list} to {station_name}")
                                            if station_name == self.temp_list[-1][-1]:
                                                self.temp_list[2].append(self.query_port)
                                                # journey_data = self.temp_list
                                                adj_ip = ""
                                                for address in self.adjacent_addresses:
                                                    if int(address.split(':')[1]) == port_number:
                                                        adj_ip = address.split(":")[0]
                                                adjacent_addr = (adj_ip, port_number)
                                                journey_data_str = '|'.join([str(item) for item in self.temp_list])
                                                # self.udp_socket.sendto(json.dumps(journey_data).encode("utf-8"), adjacent_addr)
                                                self.udp_socket.sendto(journey_data_str.encode("utf-8"), adjacent_addr)
                                                self.visited.append(station_name)
                                                self.temp_list = self.journey
                                                print(f"sent {journey_data_str} to {adjacent_addr}")
                        
                        print("end of timetable")
                        # Checks if its past midnight
                        if midnight == 0:
                            print("midnight")
                            self.temp_list[0].append("midnight")
                            # journey_data = self.temp_list
                            journey_data_str = '|'.join([str(item) for item in self.temp_list])
                            port_number = int(self.temp_list[2][-1])
                            adj_ip = ""
                            for address in self.adjacent_addresses:
                                if int(address.split(':')[1]) == port_number:
                                    adj_ip = address.split(":")[0]
                            adjacent_addr = (adj_ip, port_number)

                            # self.udp_socket.sendto(json.dumps(journey_data).encode("utf-8"), adjacent_addr)
                            self.udp_socket.sendto(journey_data_str.encode("utf-8"), adjacent_addr)
                        
        except KeyboardInterrupt:
            pass

    def load_timetable(self):
        try:
            with open(self.timetable_filename, 'r') as file:
                reader = csv.reader(file)
                self.timetable = list(reader)
        except FileNotFoundError:
            print(f"Timetable file '{self.timetable_filename}' not found for station '{self.station_name}'")

if __name__ == "__main__":
    import sys

    if len(sys.argv) <= 4:
        print("Usage: python3 ./station-server station-name browser-port query-port adjacent-ports")
        sys.exit(1)

    station_name = sys.argv[1]
    browser_port = sys.argv[2]
    query_port = sys.argv[3]
    # adjacent_ports = [int(port_str.split(':')[1]) for port_str in sys.argv[4:]]
    adjacent_addrs = sys.argv[4:]
    print(adjacent_addrs)

    # Create and start the NetworkServer instance
    server = NetworkServer(station_name, browser_port, query_port, adjacent_addrs)
    server.start()
    if server.is_alive():
        print("Child process is still running.")
    else:
        print("Child process has terminated.")

    server.join()

