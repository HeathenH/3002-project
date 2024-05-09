import multiprocessing
import socket
import csv
import json
import time
from datetime import datetime
import copy
import os

class NetworkServer(multiprocessing.Process):
    def __init__(self, station_name, browser_port, query_port, adjacent_ports):
        super().__init__()
        self.station_name = station_name
        self.browser_port = int(browser_port)
        self.query_port = int(query_port)
        self.adjacent_ports = [int(port_str) for port_str in adjacent_ports]
        self.host_ip = "127.0.0.1"
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

        print(f"Station Server '{self.station_name}' started. TCP Port: {self.browser_port}, UDP Port: {self.query_port}, Neighbour UDP Ports: {self.adjacent_ports}")
        
        # Start UDP handler
        udp_handler = multiprocessing.Process(target=self.handle_udp)
        udp_handler.start()

        # Ping adjacent ports for their station name and port number
        while len(self.station_list) != len(self.adjacent_ports):
            query_data = "query_station"
            for port in self.adjacent_ports:
                neighboring_station_address = ("127.0.0.1", port)
                self.udp_socket.sendto(query_data.encode("utf-8"), neighboring_station_address)
                time.sleep(1)

            if not self.station_list_queue.empty():
                self.station_list = self.station_list_queue.get()
            #print(f"station list: {self.station_list}")
            #print(f"station length: {len(self.station_list)}")
                
        # Code to check timetable, not working concurrently with the rest.
        """
        while True:
            # Check for timetable file changes
            current_modified_time = os.stat(self.timetable_filename).st_mtime
            #print(f"1: {current_modified_time}")
            #print(f"2: {self.last_modified_time}")
            if current_modified_time != self.last_modified_time:
                # Timetable file has changed
                self.last_modified_time = current_modified_time
                self.load_timetable()
                print("Timetable updated")
            
            time.sleep(1)  # Check every 1 second for changes
        """  
        try:
            tcp_handler = multiprocessing.Process(target=self.handle_tcp)
            tcp_handler.start()
            #tcp_handler.join()
            while True:
                # Check for timetable file changes
                current_modified_time = os.stat(self.timetable_filename).st_mtime
                #print(f"1: {current_modified_time}")
                #print(f"2: {self.last_modified_time}")
                if current_modified_time != self.last_modified_time:
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
                request_data = tcp_conn.recv(4096).decode("utf-8")
                if request_data:
                    http_method, http_path, _ = request_data.split(" ", 2)
                    if http_method == "GET" and http_path.startswith("/?to="):
                        self.visited = [self.station_name]
                        self.destination = http_path.split("=")[1]
                        self.journey[0][2] = self.destination
                        self.hard_temp = copy.deepcopy(self.journey)
                        #print(f"true origin: {self.hard_temp}")
                        
                        # Start linear search of the time from the timetable from the 4th item
                        for sublist in self.timetable[3:]:
                            time_in_sublist = sublist[0]  # set time
                            # Convert string time to datetime objects
                            time_in_timetable_datetime = datetime.strptime(time_in_sublist, "%H:%M")
                            start_time_datetime = datetime.strptime(self.start_time, "%H:%M")
                            #print(f"time: {time_in_sublist} station: {sublist[-1]}")
                            #print(f"{self.start_time}")
                            if time_in_timetable_datetime >= start_time_datetime: # Compare time
                                for station in self.visited: #check for past station visited.
                                    if sublist[-1] == station:
                                        self.counter += 1
                                if self.counter > 0: # If more than 0, it means the station has been visited before, resets counter
                                    self.counter = 0
                                    continue
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
                                        self.journey = self.hard_temp
                                        break
                                    else:
                                        for port in self.station_list:
                                            station_name = port[0]
                                            port_number = port[1]
                                            if station_name == self.journey[-1][-1]:
                                                print(f"{self.station_list}")
                                                print(f"station name: {station_name}")
                                                print(f"{self.journey[-1][-1]}")
                                                journey_data = self.journey
                                                adjacent_addr = ("127.0.0.1", port_number)
                                                self.udp_socket.sendto(json.dumps(journey_data).encode("utf-8"), adjacent_addr)
                                                self.visited.append(station_name)
                                                print(f"{journey_data}")
                                                print(f"sent journey data to {port_number}")
                                                self.journey = self.hard_temp

                        print("end of timetable")
                        
                        while len(self.journey_list) < 1:
                            time.sleep(2)
                            if not self.journey_list_queue.empty():
                                self.journey_list = self.journey_list_queue.get()
                                
                        print(f"final Journeys End: {self.journey_list}")
                        
                        # If more than one journey returned, find the fastest journey, taking into account midnights
                        # 10+ servers scenario handler
                        # wrong logic, redo it, just compare the latest time of arrival in the final destination
                        if len(self.journey_list) > 1:
                            shortest= []
                            total = 0
                            for journ in self.journey_list:
                                if journ[0][-1] == "midnight":
                                    continue
                                else:
                                    shortest = journ
                                    total = journ[1][-1]
                                    break
                            if total == 0:
                                # All journey returned are past midnight
                                self.journey_list = []
                            else:
                                for journey in self.journey_list:
                                    duration = journey[1][-1]
                                    if duration < total:
                                        total = journey[0][-1]
                                        shortest = journey
                                    else:
                                        continue
                                self.journey_list = shortest
                        
                        

                        # Handle TCP request
                        response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: Closed\r\n\r\n"
                        response += f"<html><body><h1>Journey from {self.station_name} to {self.destination}</h1>\n"
                        
                        #print(f"{self.journey_list}")
                        if self.journey_list == []:
                            response += f"<p>there is no journey from {self.station_name} to {self.destination} leaving after time-T today</p>"
                        else:
                            for steps in self.journey_list[0][3:]:
                                response += f"<p>Catch {steps[1]} from {steps[2]}, at time {steps[0]}, to arrive at {steps[4]} at time {steps[3]}.</p>\n"
                            
                        response += f"<p>Final Journey's End: {self.journey_list}</p>"
                        response += "</body></html>"
                        tcp_conn.sendall(response.encode("utf-8"))
                        self.journey_list = []
                        #print(f"journey list emptied: {self.journey_list}")
                        #print(f"Initial journey list queue size: {self.journey_list_queue.qsize()}")
                        while not self.journey_list_queue.empty():
                            self.journey_list_queue.get()
                            #print(f"journey list queue: {self.journey_list_queue}")
                            #print(f"Journey list queue size after dequeuing: {self.journey_list_queue.qsize()}")
                            
                        #print(f"final journey list queue: {self.journey_list_queue}")
                        #print(f"final journey list queue size: {self.journey_list_queue.qsize()}")
                        

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
                    station_data = [self.station_name, self.query_port, "station_port"]
                    station_json = json.dumps(station_data)
                    self.udp_socket.sendto(station_json.encode("utf-8"), addr)
                    print(f"sent station data to {addr}")
                elif "station_port" in data.decode("utf-8"):
                    station_list = json.loads(data.decode("utf-8"))
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
                    
                        journey_list = json.loads(data.decode("utf-8"))
                        print(f"current journey_list{journey_list}")
                        if len(journey_list[2]) > 1:
                            journey_list[2].pop(-1)
                            port_number = int(journey_list[2][-1])
                            journey_data = journey_list
                            address = ("127.0.0.1", port_number)
                            self.udp_socket.sendto(json.dumps(journey_data).encode("utf-8"), address)
                        else:
                            self.journey_list = []
                            print(f"ports: {journey_list[2]}")
                            print(f"before appending: {self.journey_list}")
                            self.journey_list.append(journey_list)
                            self.journey_list_queue.put(self.journey_list)
                            #print(f"journey ended: {self.journey_list}")
                        
                    else:
                        self.temp_list = json.loads(data.decode("utf-8"))
                        self.journey = copy.deepcopy(self.temp_list)
                        self.visited = self.temp_list[1]
                        midnight = 0
                        for sublist in self.timetable[3:]:
                            time_in_sublist = sublist[0]  # set time
                            time_in_timetable_datetime = datetime.strptime(time_in_sublist, "%H:%M")
                            latest_time_datetime = datetime.strptime(self.temp_list[-1][3], "%H:%M")
                            #print(f"time: {time_in_sublist} station: {sublist[-1]}")
                            #print(f"{latest_time_datetime}")
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
                                    
                                    #print(f"current udp list {self.temp_list}")
                                    if self.temp_list[-1][-1] == self.temp_list[0][2]: # Compare latest journey, end journey if match
                                        self.temp_list[0].append("ended")
                                        print(f"journey ended {self.temp_list[-1][-1]}")
                                        print(f"journey ended {self.temp_list[0][2]}")
                                        journey_data = self.temp_list
                                        port_number = int(self.temp_list[2][-1])
                                        address = ("127.0.0.1", port_number)
                                        self.udp_socket.sendto(json.dumps(journey_data).encode("utf-8"), address)
                                        self.visited.append(self.temp_list[-1][-1])
                                        self.temp_list = self.journey
                                        print(f"sent final {journey_data} to {address}")
                                    else:
                                        for port in self.station_list:
                                            station_name = port[0]
                                            port_number = port[1]
                                            print(f"attempt to send {self.temp_list} to {station_name}")
                                            if station_name == self.temp_list[-1][-1]:
                                                self.temp_list[2].append(self.query_port)
                                                journey_data = self.temp_list
                                                adjacent_addr = ("127.0.0.1", port_number)
                                                self.udp_socket.sendto(json.dumps(journey_data).encode("utf-8"), adjacent_addr)
                                                self.visited.append(station_name)
                                                self.temp_list = self.journey
                                                print(f"sent {journey_data} to {adjacent_addr}")
                        
                        print("end of timetable")
                        # Checks if its past midnight
                        if midnight == 0:
                            print("midnight")
                            self.temp_list[0].append("midnight")
                            journey_data = self.temp_list
                            port_number = int(self.temp_list[0][1])
                            address = ("127.0.0.1", port_number)
                            self.udp_socket.sendto(json.dumps(journey_data).encode("utf-8"), address)
                        
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
    adjacent_ports = [int(port_str.split(':')[1]) for port_str in sys.argv[4:]]

    # Create and start the NetworkServer instance
    server = NetworkServer(station_name, browser_port, query_port, adjacent_ports)
    server.start()
    server.join()


