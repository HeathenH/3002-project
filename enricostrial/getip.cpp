#include <iostream>
#include <ifaddrs.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <string>

using namespace std;

string get_host_ip() {
    struct ifaddrs* ifap, *ifa;
    struct sockaddr_in* sa;
    char* addr;

    if (getifaddrs(&ifap) == 0) {
        for (ifa = ifap; ifa != NULL; ifa = ifa->ifa_next) {
            if (ifa->ifa_addr->sa_family == AF_INET) { // check it is IP4
                sa = (struct sockaddr_in*)ifa->ifa_addr;
                addr = inet_ntoa(sa->sin_addr); // convert binary to text form
                // Skip localhost and look for a valid IP
                if (string(addr) != "127.0.0.1") {
                    string ip(addr);
                    freeifaddrs(ifap);
                    return ip;
                }
            }
        }
        freeifaddrs(ifap);
    }
    return "127.0.0.1"; // Fallback to localhost if no other IP found
}

int main() {
    string ip = get_host_ip();
    cout << "Current IP Address: " << ip << endl;
    return 0;
}
