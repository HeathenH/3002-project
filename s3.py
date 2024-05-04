import sys
import socket
import os
import csv
import multiprocessing
import subprocess
import json

class NetworkServer(multiprocessing.Process):
    def __init__(self, station_name, browser_port, query_port, adjacent_port):
        super().__init__()
        self.station_name = station_name
        self.browser_port = int(browser_port)
        self.query_port = int(query_port)
        adj_name, port_str = adjacent_port.split(":")
        self.adjacent_port = int(port_str)
        self.host_ip = "127.0.0.1"
        self.timetable_filename = f"tt-{self.station_name}"
        self.timetable = None

    def run(self):
        # Load timetable
        self.load_timetable()

        # Initialize TCP server
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_socket.bind((self.host_ip, self.browser_port))
        self.tcp_socket.listen(5)

        # Initialize UDP socket
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind((self.host_ip, self.query_port))

        print(f"Station Server '{self.station_name}' started. TCP Port: {self.browser_port}, UDP Port: {self.query_port}, Neighbour UDP Port: {self.adjacent_port}")

        try:
            # Start serving TCP and UDP concurrently
            tcp_handler = multiprocessing.Process(target=self.handle_tcp)
            udp_handler = multiprocessing.Process(target=self.handle_udp)

            tcp_handler.start()
            udp_handler.start()

            tcp_handler.join()
            udp_handler.join()

        except KeyboardInterrupt:
            pass
        finally:
            self.tcp_socket.close()
            self.udp_socket.close()

    def handle_tcp(self):
        try:
            while True:
                tcp_conn, _ = self.tcp_socket.accept()
                request_data = tcp_conn.recv(1024).decode("utf-8")
                if request_data:
                    http_method, http_path, _ = request_data.split(" ", 2)
                    if http_method == "GET" and http_path.startswith("/?to="):
                        # Handle TCP request
                        response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: Closed\r\n\r\n"
                        response += f"<html><body><h1>Timetable for {self.station_name}</h1>\n"
                        if self.timetable:
                            for row in self.timetable:
                                response += f"<p>{', '.join(row)}</p>\n"
                        else:
                            response += "<p>Timetable not available</p>"
                        response += "</body></html>"
                        tcp_conn.sendall(response.encode("utf-8"))
                        
                        # Send UDP query
                        neighboring_station_address = ("127.0.0.1", self.adjacent_port)
                        query_data = "query_timetable"
                        self.udp_socket.sendto(query_data.encode("utf-8"), neighboring_station_address)
                        print(f"sent query_timetable to {self.adjacent_port}")
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
                data, addr = self.udp_socket.recvfrom(1024)
                if "query_timetable" in data.decode("utf-8"):
                    neighboring_station_address = ("127.0.0.1", self.adjacent_port)
                    timetable_data = self.timetable
                    timetable_data.pop(2)
                    timetable_data.pop(0)
                    del timetable_data[0][2]
                    del timetable_data[0][1]
                    timetable_json = json.dumps(timetable_data)
                    if timetable_data:
                        self.udp_socket.sendto(timetable_json.encode("utf-8"), neighboring_station_address)
                        print(f"sent timetable to {neighboring_station_address}")
                    else:
                        print("Timetable data is not available.")
                        
                if "TerminalA" in data.decode("utf-8") or "JunctionB" in data.decode("utf-8"):
                    #print("recieved station name")
                    # Decode the JSON string back into a list of lists
                    received_timetable_data = json.loads(data.decode("utf-8"))
                    print(f"Timetable recieved: {received_timetable_data}")
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
    if len(sys.argv) != 5:
        print("Usage: python3 ./station-server station-name browser-port query-port adjacent-port")
        sys.exit(1)

    station_name = sys.argv[1]
    browser_port = sys.argv[2]
    query_port = sys.argv[3]
    adjacent_port = sys.argv[4]

    # Create and start the NetworkServer instance
    server = NetworkServer(station_name, browser_port, query_port, adjacent_port)
    server.start()
    server.join()
