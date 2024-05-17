#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <thread>
#include <mutex>
#include <queue>
#include <algorithm>
#include <chrono>
#include <ctime>
#include <cstring>
#include <cstdlib>
#include <cstdio>
#include <unistd.h>
#include <cctype>
#include <locale>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/stat.h>

using namespace std;

class NetworkServer {
public:
    NetworkServer(string station_name, int browser_port, int query_port, vector<pair<string, int>> adjacent_servers)
        : station_name(station_name), browser_port(browser_port), query_port(query_port), adjacent_servers(adjacent_servers) {
        host_ip = "172.27.72.141";
        timetable_filename = "tt-" + station_name;
        last_modified_time = 0;
        start_time = "9:00";
        load_timetable();
    }

    void run() {
        // Initialize TCP server
        tcp_socket = socket(AF_INET, SOCK_STREAM, 0);
        if (tcp_socket < 0) {
            cerr << "Error creating TCP socket" << endl;
            exit(1);
        }
        sockaddr_in tcp_server_addr;
        tcp_server_addr.sin_family = AF_INET;
        tcp_server_addr.sin_port = htons(browser_port);
        inet_pton(AF_INET, host_ip.c_str(), &tcp_server_addr.sin_addr);
        if (bind(tcp_socket, (sockaddr*)&tcp_server_addr, sizeof(tcp_server_addr)) < 0) {
            cerr << "Error binding TCP socket" << endl;
            exit(1);
        }
        if (listen(tcp_socket, 5) < 0) {
            cerr << "Error listening on TCP socket" << endl;
            exit(1);
        }

        // Initialize UDP socket
        udp_socket = socket(AF_INET, SOCK_DGRAM, 0);
        if (udp_socket < 0) {
            cerr << "Error creating UDP socket" << endl;
            exit(1);
        }
        sockaddr_in udp_server_addr;
        udp_server_addr.sin_family = AF_INET;
        udp_server_addr.sin_port = htons(query_port);
        inet_pton(AF_INET, host_ip.c_str(), &udp_server_addr.sin_addr);
        if (bind(udp_socket, (sockaddr*)&udp_server_addr, sizeof(udp_server_addr)) < 0) {
            cerr << "Error binding UDP socket" << endl;
            exit(1);
        }

        cout << "Station Server '" << station_name << "' started. TCP Port: " << browser_port << ", UDP Port: " << query_port << ", Neighbour UDP Ports: ";
        for (const auto& server : adjacent_servers) {
            cout << server.first << ":" << server.second << " ";
        }
        cout << endl;

        thread udp_handler(&NetworkServer::handle_udp, this);
        udp_handler.detach();

        while (station_list.size() != adjacent_servers.size()) {
            string query_data = "query_station";
            for (const auto& server : adjacent_servers) {
                sockaddr_in neighboring_station_addr;
                neighboring_station_addr.sin_family = AF_INET;
                neighboring_station_addr.sin_port = htons(server.second);
                inet_pton(AF_INET, server.first.c_str(), &neighboring_station_addr.sin_addr);
                sendto(udp_socket, query_data.c_str(), query_data.size(), 0, (sockaddr*)&neighboring_station_addr, sizeof(neighboring_station_addr));
                this_thread::sleep_for(chrono::seconds(1));
            }

            if (!station_list_queue.empty()) {
                lock_guard<mutex> lock(queue_mutex);
                station_list = station_list_queue.front();
                station_list_queue.pop();
            }
            cout << "station list: ";
            for (auto& station : station_list) {
                cout << station[0] << " ";
            }
            cout << endl;
        }

        thread tcp_handler(&NetworkServer::handle_tcp, this);
        tcp_handler.detach();

        while (true) {
            this_thread::sleep_for(chrono::seconds(1));
            auto current_modified_time = get_last_modified_time(timetable_filename);
            if (current_modified_time != last_modified_time) {
                last_modified_time = current_modified_time;
                load_timetable();
                cout << "Timetable updated" << endl;
            }
        }
    }

private:
    string station_name;
    int browser_port;
    int query_port;
    vector<pair<string, int>> adjacent_servers;
    string host_ip;
    string timetable_filename;
    time_t last_modified_time;
    int tcp_socket;
    int udp_socket;
    vector<vector<string>> timetable;
    vector<vector<string>> station_list;
    queue<vector<vector<string>>> station_list_queue;
    queue<vector<vector<string>>> journey_list_queue;
    string destination;
    vector<vector<string>> journey;
    vector<vector<string>> hard_temp;
    string start_time;
    vector<string> visited;
    int counter = 0;
    vector<vector<vector<string>>> journey_list;
    vector<vector<string>> temp_list;
    mutex queue_mutex;

bool isValidRoute(const std::string& currentStation, const std::string& targetDestination, const std::vector<std::string>& adjacentStations) {
    // Trim whitespace
    std::string trimmedCurrent = currentStation;
    std::string trimmedTarget = targetDestination;
    trim(trimmedCurrent);
    trim(trimmedTarget);

    // Check if current station is the target destination
    if (trimmedCurrent == trimmedTarget) {
        return true;
    }

    // Check if current station is in the list of adjacent stations
    for (const auto& station : adjacentStations) {
        std::string trimmedStation = station;
        trim(trimmedStation);
        if (trimmedCurrent == trimmedStation) {
            return true;
        }
    }

    return false;
}


void handle_tcp() {
    try {
        while (true) {
            cout << "[DEBUG] Waiting to accept a new connection..." << endl;

            sockaddr_in client_addr;
            socklen_t client_len = sizeof(client_addr);
            int client_socket = accept(tcp_socket, (sockaddr*)&client_addr, &client_len);
            if (client_socket < 0) {
                cerr << "[ERROR] Error accepting connection" << endl;
                continue;
            }
            cout << "[DEBUG] Accepted connection from " << inet_ntoa(client_addr.sin_addr) << ":" << ntohs(client_addr.sin_port) << endl;

            char buffer[4096];
            int bytes_received = recv(client_socket, buffer, sizeof(buffer), 0);
            if (bytes_received < 0) {
                cerr << "[ERROR] Error reading from socket" << endl;
                close(client_socket);
                continue;
            }
            buffer[bytes_received] = '\0';
            string request(buffer);
            cout << "[DEBUG] Received request: " << request << endl;

            stringstream ss(request);
            string http_method, http_path, http_version;
            ss >> http_method >> http_path >> http_version;

            cout << "[DEBUG] HTTP Method: " << http_method << ", HTTP Path: " << http_path << ", HTTP Version: " << http_version << endl;

            if (http_method == "GET" && http_path.find("/?to=") != string::npos) {
                visited = {station_name};
                destination = http_path.substr(http_path.find("=") + 1);
                trim(destination);  // Trim the destination
                journey = {{"odyssey", to_string(query_port), destination}, {station_name}, {to_string(query_port)}};
                hard_temp = journey;
                journey_list.clear();

                cout << "[DEBUG] Processing journey from " << station_name << " to " << destination << endl;

                for (auto& sublist : timetable) {
                    string time_in_sublist = sublist[0];
                    auto time_in_timetable_datetime = parse_time(time_in_sublist);
                    auto start_time_datetime = parse_time(start_time);

                    cout << "[DEBUG] Checking timetable entry with time " << time_in_sublist << endl;

                    if (time_in_timetable_datetime >= start_time_datetime) {
                        cout << "[DEBUG] Entry is valid as it is after the start time" << endl;

                        if (find(visited.begin(), visited.end(), sublist.back()) != visited.end()) {
                            cout << "[DEBUG] Station " << sublist.back() << " already visited, skipping" << endl;
                            continue;
                        }

                        string next_station = sublist.back();
                        trim(next_station);

                        vector<string> adjacent_stations;
                        for (const auto& port : station_list) {
                            adjacent_stations.push_back(port[0]);
                        }

                        if (isValidRoute(next_station, destination, adjacent_stations)) {
                            cout << "[DEBUG] Adding sublist to journey: ";
                            for (const auto& item : sublist) {
                                cout << item << " ";
                            }
                            cout << endl;

                            journey.push_back(sublist);
                            journey[1].push_back(next_station);

                            string current_destination = journey.back().back();
                            trim(current_destination);  // Trim the current destination
                            cout << "[DEBUG] Comparing journey destination: " << current_destination << " with target destination: " << destination << endl;

                            if (current_destination == destination) {
                                cout << "[DEBUG] Destination " << destination << " reached" << endl;
                                journey[0].push_back("ended");
                                journey_list.push_back(journey);
                                journey = hard_temp;
                                break;
                            } else {
                                cout << "[DEBUG] Journey not yet completed, checking adjacent stations" << endl;

                                for (auto& port : station_list) {
                                    cout << "[DEBUG] port[0]: " << port[0] << ", journey.back().back(): " << journey.back().back() << endl;

                                    string trimmed_port = port[0];
                                    string trimmed_journey_back = journey.back().back();
                                    trim(trimmed_port);
                                    trim(trimmed_journey_back);

                                    if (trimmed_port == trimmed_journey_back) {
                                        string journey_data = serialize_journey(journey);
                                        sockaddr_in adjacent_addr;
                                        adjacent_addr.sin_family = AF_INET;
                                        adjacent_addr.sin_port = htons(stoi(port[1]));
                                        inet_pton(AF_INET, host_ip.c_str(), &adjacent_addr.sin_addr);

                                        cout << "[DEBUG] Sending journey data to adjacent station " << port[0] << " on port " << port[1] << endl;
                                        ssize_t udp_bytes_sent = sendto(udp_socket, journey_data.c_str(), journey_data.size(), 0, (sockaddr*)&adjacent_addr, sizeof(adjacent_addr));
                                        cout << "[DEBUG] Sent " << udp_bytes_sent << " bytes via UDP to port " << port[1] << endl;

                                        visited.push_back(port[0]);
                                        journey = hard_temp;
                                    }
                                }
                            }
                        }
                    }
                }

                cout << "[DEBUG] Waiting for journey completion..." << endl;

                bool journey_completed = false;
                int wait_counter = 0; // to prevent infinite loop

                while (!journey_completed && wait_counter < 10) { // add a condition to avoid infinite loop
                    {
                        lock_guard<mutex> lock(queue_mutex);
                        cout << "[DEBUG] Lock acquired, checking journey_list_queue" << endl;

                        while (!journey_list_queue.empty()) {
                            journey_list.push_back(journey_list_queue.front());
                            journey_list_queue.pop();
                            cout << "[DEBUG] Journey added to journey_list" << endl;
                        }
                    }

                    if (!journey_list.empty()) {
                        cout << "[DEBUG] journey_list is not empty, breaking out of the loop" << endl;
                        journey_completed = true;
                        break;
                    }

                    wait_counter++;
                    cout << "[DEBUG] journey_list is still empty, sleeping for 1 second (attempt " << wait_counter << ")" << endl;
                    this_thread::sleep_for(chrono::seconds(1));
                }

                // Filter out invalid journeys
                journey_list.erase(
                    remove_if(journey_list.begin(), journey_list.end(), [](const vector<vector<string>>& journey) {
                        return journey.size() < 2 || journey[0].back() != "ended";
                    }),
                    journey_list.end()
                );

                if (journey_list.size() > 1) {
                    cout << "[DEBUG] Multiple journeys found, selecting the shortest one" << endl;
                    auto shortest = *min_element(journey_list.begin(), journey_list.end(),
                        [this](const vector<vector<string>>& a, const vector<vector<string>>& b) {
                            return parse_time(a.back()[3]) < parse_time(b.back()[3]);
                        });
                    journey_list = {shortest};
                }

                // Print the journey_list for debugging
                print_journey_list(journey_list);

                cout << "[DEBUG] Journey completed. Forming response..." << endl;

                string response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: Closed\r\n\r\n";
                response += "<!DOCTYPE html><html><body><h1>Journey from " + station_name + " to " + destination + " at " + start_time + "</h1>\n";
                if (journey_list.empty()) {
                    response += "<p>There is no journey from " + station_name + " to " + destination + " leaving after " + start_time + " today.</p>";
                } else {
                    cout << "[DEBUG] Journey list size: " << journey_list.size() << endl;
                    for (const auto& journey : journey_list) {
                        cout << "[DEBUG] Processing journey with " << journey.size() << " steps." << endl;
                        for (const auto& step : journey) {
                            if (step.size() < 5) {
                                cerr << "[ERROR] Invalid step data: expected at least 5 elements, got " << step.size() << endl;
                                continue;
                            }
                            cout << "[DEBUG] step[0]: " << step[0] << " step[1]: " << step[1] << " step[2]: " << step[2] << " step[3]: " << step[3] << " step[4]: " << step[4] << endl;
                            response += "Catch " + step[1] + " from " + step[2] + ", at time " + step[0] + ", to arrive at " + step[4] + " at time " + step[3] + ".\n";
                        }
                    }
                }
                response += "</body></html>";

                cout << "[DEBUG] Formed response: " << response << endl;

                ssize_t bytes_sent = send(client_socket, response.c_str(), response.size(), 0);
                if (bytes_sent < 0) {
                    cerr << "[ERROR] Error sending response: " << strerror(errno) << endl;
                } else {
                    cout << "[DEBUG] Sent " << bytes_sent << " bytes" << endl;
                }

                if (bytes_sent < response.size()) {
                    cerr << "[ERROR] Incomplete response sent. Expected: " << response.size() << ", Sent: " << bytes_sent << endl;
                } else {
                    cout << "[DEBUG] Entire response sent successfully" << endl;
                }
            } else {
                string response = "HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\nConnection: Closed\r\n\r\n";
                response += "<html><body><h1>404 Not Found</h1></body></html>";
                ssize_t bytes_sent = send(client_socket, response.c_str(), response.size(), 0);
                if (bytes_sent < 0) {
                    cerr << "[ERROR] Error sending 404 response: " << strerror(errno) << endl;
                } else {
                    cout << "[DEBUG] Sent 404 response: " << response << endl;
                }
            }
            close(client_socket);
            cout << "[DEBUG] Connection closed" << endl;
        }
    } catch (const exception& e) {
        cerr << "[ERROR] Error in handle_tcp: " << e.what() << endl;
    }
}

void handle_udp() {
    try {
        cout << "[DEBUG] handle_udp is called" << endl;
        while (true) {
            char buffer[4096];
            sockaddr_in sender_addr;
            socklen_t sender_len = sizeof(sender_addr);
            int bytes_received = recvfrom(udp_socket, buffer, sizeof(buffer), 0, (sockaddr*)&sender_addr, &sender_len);
            if (bytes_received < 0) {
                cerr << "[ERROR] Error receiving UDP data" << endl;
                continue;
            }
            buffer[bytes_received] = '\0';
            string data(buffer);
            cout << "[DEBUG] Received UDP data from " << inet_ntoa(sender_addr.sin_addr) << ":" << ntohs(sender_addr.sin_port) << " - " << data << endl;

            if (data == "query_station") {
                vector<vector<string>> station_data = {{station_name, to_string(query_port), "station_port"}};
                string station_json = serialize_journey(station_data);
                sendto(udp_socket, station_json.c_str(), station_json.size(), 0, (sockaddr*)&sender_addr, sender_len);
                cout << "[DEBUG] Sent station data to " << inet_ntoa(sender_addr.sin_addr) << ":" << ntohs(sender_addr.sin_port) << endl;
            } else if (data.find("station_port") != string::npos) {
                vector<vector<string>> station_list_data = deserialize_journey(data);
                lock_guard<mutex> lock(queue_mutex);
                if (find_if(station_list.begin(), station_list.end(), [&](const vector<string>& item) { return item[1] == station_list_data[0][1]; }) == station_list.end()) {
                    station_list.push_back(station_list_data[0]);
                    station_list_queue.push(station_list);
                }
                cout << "[DEBUG] Updated station list: ";
                for (auto& station : station_list) {
                    cout << station[0] << " ";
                }
                cout << endl;
            } else if (data.find("odyssey") != string::npos) {
                cout << "[DEBUG] Received journey data: " << data << endl;
                vector<vector<string>> received_journey = deserialize_journey(data);
                cout << "[DEBUG] Deserialized journey: " << serialize_journey(received_journey) << endl;

                if (received_journey[0].back() == "ended" || received_journey[0].back() == "midnight") {
                    lock_guard<mutex> lock(queue_mutex);
                    journey_list_queue.push(received_journey);
                    cout << "[DEBUG] Journey completed and added to queue: " << serialize_journey(received_journey) << endl;
                } else {
                    temp_list = received_journey;
                    journey = temp_list;
                    visited = temp_list[1];
                    int midnight = 0;

                    for (auto& sublist : timetable) {
                        string time_in_sublist = sublist[0];
                        auto time_in_timetable_datetime = parse_time(time_in_sublist);
                        auto latest_time_datetime = parse_time(temp_list.back()[3]);

                        if (time_in_timetable_datetime >= latest_time_datetime) {
                            midnight++;
                            if (find(visited.begin(), visited.end(), sublist.back()) != visited.end()) {
                                continue;
                            }
                            temp_list.push_back(sublist);
                            temp_list[1].push_back(sublist.back());

                            cout << "[DEBUG] Updated temp_list: " << serialize_journey(temp_list) << endl;
                            cout << "[DEBUG] temp_list.back().back(): " << temp_list.back().back() << ", destination: " << temp_list[0][2] << endl;

                            std::string temp1 = temp_list.back().back();
                            std::string temp2 = temp_list[0][2];
                            trim(temp1);
                            trim(temp2);

                            vector<string> adjacent_stations;
                            for (const auto& port : station_list) {
                                adjacent_stations.push_back(port[0]);
                            }

                            if (isValidRoute(temp1, temp2, adjacent_stations)) {
                                if (temp1 == temp2) {
                                    temp_list[0].push_back("ended");
                                    string journey_data = serialize_journey(temp_list);
                                    sendto(udp_socket, journey_data.c_str(), journey_data.size(), 0, (sockaddr*)&sender_addr, sizeof(sender_addr));
                                    visited.push_back(temp_list.back().back());
                                    temp_list = journey;
                                    cout << "[DEBUG] Journey ended: " << serialize_journey(temp_list) << endl;
                                } else {
                                    for (auto& port : station_list) {
                                        cout << "[DEBUG] Checking station: " << port[0] << " on port: " << port[1] << endl;

                                        string trimmed_port = port[0];
                                        string trimmed_journey_back = journey.back().back();
                                        trim(trimmed_port);
                                        trim(trimmed_journey_back);

                                        if (trimmed_port == trimmed_journey_back) {
                                            cout << "[DEBUG] Matched station: " << port[0] << " on port: " << port[1] << endl;
                                            string journey_data = serialize_journey(journey);
                                            sockaddr_in adjacent_addr;
                                            adjacent_addr.sin_family = AF_INET;
                                            adjacent_addr.sin_port = htons(stoi(port[1]));
                                            inet_pton(AF_INET, host_ip.c_str(), &adjacent_addr.sin_addr);

                                            cout << "[DEBUG] Sending journey data to adjacent station " << port[0] << " on port " << port[1] << endl;
                                            ssize_t udp_bytes_sent = sendto(udp_socket, journey_data.c_str(), journey_data.size(), 0, (sockaddr*)&adjacent_addr, sizeof(adjacent_addr));
                                            cout << "[DEBUG] Sent " << udp_bytes_sent << " bytes via UDP to port " << port[1] << endl;

                                            cout << "[DEBUG] Current journey: " << serialize_journey(journey) << endl;

                                            visited.push_back(port[0]);
                                            journey = hard_temp;
                                        }
                                    }
                                }
                            }
                        }
                    }

                    if (midnight == 0) {
                        temp_list[0].push_back("midnight");
                        string journey_data = serialize_journey(temp_list);
                        sendto(udp_socket, journey_data.c_str(), journey_data.size(), 0, (sockaddr*)&sender_addr, sizeof(sender_addr));
                        cout << "[DEBUG] Journey past midnight: " << serialize_journey(temp_list) << endl;
                    }
                }
            }
        }
    } catch (const exception& e) {
        cerr << "[ERROR] Error in handle_udp: " << e.what() << endl;
    }
}

void load_timetable() {
    ifstream file(timetable_filename);
    if (!file.is_open()) {
        cerr << "Timetable file '" << timetable_filename << "' not found for station '" << station_name << "'" << endl;
        return;
    }
    timetable.clear();
    string line;

    // Skip the first two lines
    getline(file, line); // Skip header line #1
    getline(file, line); // Skip header line #2

    while (getline(file, line)) {
        cout << "[DEBUG] Reading line: " << line << endl;
        stringstream ss(line);
        string item;
        vector<string> row;
        while (getline(ss, item, ',')) {
            cout << "[DEBUG] Parsed item: " << item << endl;
            row.push_back(item);
        }
        timetable.push_back(row);
    }
    file.close();
    
    // Print the loaded timetable for verification
    cout << "[DEBUG] Timetable loaded for station '" << station_name << "'" << endl;
    for (const auto& row : timetable) {
        for (const auto& item : row) {
            cout << "[DEBUG] Stored item: " << item << " ";
        }
        cout << endl;
    }
}

time_t get_last_modified_time(const string& filename) {
    struct stat file_stat;
    if (stat(filename.c_str(), &file_stat) == -1) {
        return 0;
    }
    return file_stat.st_mtime;
}

static time_t parse_time(const string& time_str) {
    tm time_tm = {};
    strptime(time_str.c_str(), "%H:%M", &time_tm);
    return mktime(&time_tm);
}

string serialize_journey(const vector<vector<string>>& journey_data) {
    stringstream ss;
    for (const auto& row : journey_data) {
        ss << "[";
        for (const auto& item : row) {
            ss << "'" << item << "',";
        }
        if (!row.empty()) {
            ss.seekp(-1, ss.cur);  // Remove the last comma
        }
        ss << "]|";
    }
    string result = ss.str();
    if (!result.empty()) {
        result.pop_back();  // Remove the last pipe character
    }
    return result;
}


vector<vector<string>> deserialize_journey(const string& data) {
    vector<vector<string>> journey_data;
    stringstream ss(data);
    string row;
    while (getline(ss, row, '|')) {
        vector<string> journey_row;
        stringstream row_ss(row);
        string item;
        while (getline(row_ss, item, ',')) {
            // Remove leading and trailing whitespace and single quotes
            item.erase(remove(item.begin(), item.end(), '['), item.end());
            item.erase(remove(item.begin(), item.end(), ']'), item.end());
            item.erase(remove(item.begin(), item.end(), '\''), item.end());
            trim(item);
            journey_row.push_back(item);
        }
        journey_data.push_back(journey_row);
    }
    return journey_data;
}


void print_journey_list(const vector<vector<vector<string>>>& journey_list) {
    cout << "[DEBUG] Journey List:" << endl;
    for (const auto& journey : journey_list) {
        cout << "[DEBUG] Journey:" << endl;
        for (const auto& step : journey) {
            for (const auto& item : step) {
                cout << "[DEBUG] " << item << " ";
            }
            cout << endl;
        }
        cout << "[DEBUG] -----" << endl;
    }
}

// trim from start (in place)
static inline void ltrim(std::string &s) {
    s.erase(s.begin(), std::find_if(s.begin(), s.end(), [](unsigned char ch) {
        return !std::isspace(ch);
    }));
}

// trim from end (in place)
static inline void rtrim(std::string &s) {
    s.erase(std::find_if(s.rbegin(), s.rend(), [](unsigned char ch) {
        return !std::isspace(ch);
    }).base(), s.end());
}

// trim from both ends (in place)
static inline void trim(std::string &s) {
    ltrim(s);
    rtrim(s);
}
};

int main(int argc, char* argv[]) {
    if (argc <= 4) {
        cerr << "Usage: ./station_server station-name browser-port query-port adjacent-ports" << endl;
        return 1;
    }

    string station_name = argv[1];
    int browser_port = stoi(argv[2]);
    int query_port = stoi(argv[3]);
    vector<pair<string, int>> adjacent_servers;
    for (int i = 4; i < argc; ++i) {
        string addr_port_str = argv[i];
        size_t pos = addr_port_str.find(':');
        if (pos != string::npos) {
            // adjacent_ports.push_back(stoi(port_str.substr(pos + 1)));
            string ip = addr_port_str.substr(0, pos);
            int port = stoi(addr_port_str.substr(pos + 1));
            adjacent_servers.emplace_back(ip, port);
        }
    }

    NetworkServer server(station_name, browser_port, query_port, adjacent_servers);
    server.run();

    return 0;
}
