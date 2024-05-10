#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/types.h>
#include <errno.h>
#include <sys/ipc.h>
#include <sys/shm.h>
#include <signal.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <time.h>

#define MAX_STATIONS 100
#define MAX_ADJ_PORTS 10
#define MAX_BUFFER 4096
#define TIMETABLE_SIZE 1024

typedef struct {
    char station_name[50];
    int browser_port;
    int query_port;
    int num_adjacent_ports;
    int adjacent_ports[MAX_ADJ_PORTS];
} NetworkServerConfig;

typedef struct {
    char journey[1024];
    char visited[1024];
    char timetable[TIMETABLE_SIZE][5][50]; // Assuming each timetable entry has 5 fields and each field is at most 50 characters
    int last_modified_time;
} ServerState;

NetworkServerConfig serverConfig;
ServerState *serverState;

int tcp_sockfd, udp_sockfd;
pid_t tcp_pid, udp_pid;

void error(const char *msg) {
    perror(msg);
    exit(1);
}

void signal_handler(int sig) {
    if (sig == SIGCHLD) {
        // Reap the zombie processes
        while (waitpid(-1, NULL, WNOHANG) > 0) {}
    } else if (sig == SIGINT || sig == SIGTERM) {
        // Cleanup and close sockets
        close(tcp_sockfd);
        close(udp_sockfd);
        shmctl(shmid, IPC_RMID, NULL); // Assuming shmid is globally available
        kill(tcp_pid, SIGTERM);
        kill(udp_pid, SIGTERM);
        exit(0);
    }
}

void setup_tcp_server(int port) {
    struct sockaddr_in server_addr;
    tcp_sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (tcp_sockfd < 0) error("ERROR opening TCP socket");

    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(port);

    if (bind(tcp_sockfd, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0) 
        error("ERROR binding TCP socket");
    listen(tcp_sockfd, 5);
    printf("TCP Server listening on port %d\n", port);
}

void setup_udp_server(int port) {
    struct sockaddr_in server_addr;
    udp_sockfd = socket(AF_INET, SOCK_DGRAM, 0);
    if (udp_sockfd < 0) error("ERROR opening UDP socket");

    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(port);

    if (bind(udp_sockfd, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0) 
        error("ERROR binding UDP socket");
    printf("UDP Server listening on port %d\n", port);
}

void handle_tcp_connection() {
    struct sockaddr_in cli_addr;
    socklen_t clilen = sizeof(cli_addr);
    int newsockfd;
    char buffer[MAX_BUFFER];

    while (1) {
        newsockfd = accept(tcp_sockfd, (struct sockaddr *)&cli_addr, &clilen);
        if (newsockfd < 0) error("ERROR on accept");

        bzero(buffer, MAX_BUFFER);
        read(newsockfd, buffer, MAX_BUFFER - 1);
        printf("TCP Received: %s\n", buffer);
        // Process TCP request here based on `buffer`
        write(newsockfd, "Response", 8);
        close(newsockfd);
    }
}

void handle_udp_message() {
    char buffer[MAX_BUFFER];
    struct sockaddr_in cli_addr;
    socklen_t clilen = sizeof(cli_addr);
    int n;

    while (1) {
        bzero(buffer, MAX_BUFFER);
        n = recvfrom(udp_sockfd, buffer, MAX_BUFFER - 1, 0, (struct sockaddr *)&cli_addr, &clilen);
        if (n < 0) error("ERROR on recvfrom");
        printf("UDP Received: %s\n", buffer);
        // Process UDP message here based on `buffer`
        sendto(udp_sockfd, "Response", 8, 0, (struct sockaddr *)&cli_addr, clilen);
    }
}

void setup_shared_memory() {
    int shmid = shmget(IPC_PRIVATE, sizeof(ServerState), IPC_CREAT | 0666);
    if (shmid < 0) error("ERROR creating shared memory");

    serverState = (ServerState *)shmat(shmid, NULL, 0);
    if (serverState == (void *) -1) error("ERROR attaching shared memory");
}

void load_timetable(const char *filename) {
    FILE *file = fopen(filename, "r");
    if (!file) error("ERROR opening file");

    char line[256];
    int i = 0;
    while (fgets(line, sizeof(line), file) && i < TIMETABLE_SIZE) {
        sscanf(line, "%s %s %s %s %s", serverState->timetable[i][0], serverState->timetable[i][1], serverState->timetable[i][2], serverState->timetable[i][3], serverState->timetable[i][4]);
        i++;
    }
    fclose(file);
}

void monitor_file_changes(const char *filename) {
    int fd = open(filename, O_RDONLY);
    if (fd < 0) error("ERROR opening file for monitoring");

    struct stat statbuf;
    if (fstat(fd, &statbuf) < 0) error("ERROR getting file stats");

    int last_modified = statbuf.st_mtime;

    while (1) {
        sleep(1);  // Check every second
        fstat(fd, &statbuf);
        if (statbuf.st_mtime != last_modified) {
            printf("File has been modified. Reloading timetable.\n");
            load_timetable(filename);
            last_modified = statbuf.st_mtime;
        }
    }
    close(fd);
}

void process_journey_request(char *destination) {
    // Assuming destination is a station name and the journey needs to be calculated
    // This is a simplified logic to demonstrate the idea
    printf("Processing journey to %s\n", destination);
    int found = 0;
    for (int i = 0; i < TIMETABLE_SIZE; i++) {
        if (strcmp(serverState->timetable[i][4], destination) == 0) {  // Assuming the destination is in the last column
            printf("Journey found: %s at %s\n", serverState->timetable[i][1], serverState->timetable[i][0]);
            found = 1;
            break;
        }
    }
    if (!found) {
        printf("No journey found to %s\n", destination);
    }
}

void tcp_server_loop() {
    struct sockaddr_in cli_addr;
    socklen_t clilen = sizeof(cli_addr);
    int newsockfd;
    char buffer[MAX_BUFFER];

    while (1) {
        newsockfd = accept(tcp_sockfd, (struct sockaddr *)&cli_addr, &clilen);
        if (newsockfd < 0) error("ERROR on accept");

        bzero(buffer, MAX_BUFFER);
        int n = read(newsockfd, buffer, MAX_BUFFER - 1);
        if (n > 0) {
            printf("TCP Received: %s\n", buffer);
            process_journey_request(buffer);
            char response[] = "Journey details have been processed.";
            write(newsockfd, response, sizeof(response));
        }
        close(newsockfd);
    }
}

void udp_server_loop() {
    char buffer[MAX_BUFFER];
    struct sockaddr_in cli_addr;
    socklen_t clilen = sizeof(cli_addr);

    while (1) {
        bzero(buffer, MAX_BUFFER);
        int n = recvfrom(udp_sockfd, buffer, MAX_BUFFER - 1, 0, (struct sockaddr *)&cli_addr, &clilen);
        if (n > 0) {
            printf("UDP Received: %s\n", buffer);
            process_journey_request(buffer);
            char response[] = "Journey data received and processed.";
            sendto(udp_sockfd, response, sizeof(response), 0, (struct sockaddr *)&cli_addr, clilen);
        }
    }
}

int main(int argc, char *argv[]) {
    if (argc < 6) {
        fprintf(stderr, "Usage: %s station_name tcp_port udp_port filename\n", argv[0]);
        exit(1);
    }

    strcpy(serverConfig.station_name, argv[1]);
    serverConfig.browser_port = atoi(argv[2]);
    serverConfig.query_port = atoi(argv[3]);
    const char *filename = argv[4];

    setup_shared_memory();
    setup_tcp_server(serverConfig.browser_port);
    setup_udp_server(serverConfig.query_port);

    load_timetable(filename);

    signal(SIGCHLD, signal_handler);
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);

    tcp_pid = fork();
    if (tcp_pid == 0) {
        tcp_server_loop();
    } else {
        udp_pid = fork();
        if (udp_pid == 0) {
            udp_server_loop();
        } else {
            monitor_file_changes(filename);
        }
    }

    return 0;
}
