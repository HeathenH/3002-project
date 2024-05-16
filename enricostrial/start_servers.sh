#!/bin/bash

./station_server TerminalA 4001 2001 localhost:2015 &
sleep 3
./station_server JunctionB 4003 2003 localhost:2009 localhost:2015 &
sleep 3
./station_server BusportC 4005 2005 localhost:2013 localhost:2017 &
sleep 3
./station_server StationD 4007 2007 localhost:2009 &
sleep 3
./station_server TerminalE 4009 2009 localhost:2003 localhost:2007 localhost:2011 localhost:2015 &
sleep 3
./station_server JunctionF 4011 2011 localhost:2009 localhost:2015 localhost:2019 &
sleep 3
./station_server BusportG 4013 2013 localhost:2005 localhost:2019 &
sleep 3
./station_server StationH 4015 2015 localhost:2001 localhost:2003 localhost:2009 localhost:2011 localhost:2019 &
sleep 3
./station_server TerminalI 4017 2017 localhost:2005 localhost:2019 &
sleep 3
./station_server JunctionJ 4019 2019 localhost:2011 localhost:2013 localhost:2015 localhost:2017 &
