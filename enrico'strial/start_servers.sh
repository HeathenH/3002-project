#!/bin/bash

./station_server TerminalA 4101 2101 localhost:2115 &
sleep 1
./station_server JunctionB 4103 2103 localhost:2109 localhost:2115 &
sleep 1
./station_server BusportC 4105 2105 localhost:2113 localhost:2117 &
sleep 1
./station_server StationD 4107 2107 localhost:2109 &
sleep 1
./station_server TerminalE 4109 2109 localhost:2103 localhost:2107 localhost:2111 localhost:2115 &
sleep 1
./station_server JunctionF 4111 2111 localhost:2109 localhost:2115 localhost:2119 &
sleep 1
./station_server BusportG 4113 2113 localhost:2105 localhost:2119 &
sleep 1
./station_server StationH 4115 2115 localhost:2101 localhost:2103 localhost:2109 localhost:2111 localhost:2119 &
sleep 1
./station_server TerminalI 4117 2117 localhost:2105 localhost:2119 &
sleep 1
./station_server JunctionJ 4119 2119 localhost:2111 localhost:2113 localhost:2115 localhost:2117 &
