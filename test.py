import socket

message = "query_station"
server_address = ('127.0.0.1', 2003)  # Ensure this is the correct port for the server
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_socket.sendto(message.encode('utf-8'), server_address)

udp_socket.settimeout(5)
try:
    data, addr = udp_socket.recvfrom(4096)
    print(f"Received response from {addr}: {data.decode('utf-8')}")
except socket.timeout:
    print("No response received.")
