#!/bin/bash

python3 ./station-server.py TerminalA 4001 2001 172.27.86.172:2015 & 
sleep(3)
python3 ./station-server.py JunctionB 4003 2003 172.27.86.172:2009 172.27.86.172:2015 & 
sleep(3)
python3 ./station-server.py BusportC 4005 2005 172.27.86.172:2013 172.27.86.172:2017 & 
sleep(3)
python3 ./station-server.py StationD 4007 2007 172.27.86.172:2009 & 
sleep(3)
python3 ./station-server.py TerminalE 4009 2009 172.27.86.172:2003 172.27.86.172:2007 172.27.86.172:2011 172.27.86.172:2015 & 
sleep(3)
python3 ./station-server.py JunctionF 4011 2011 172.27.86.172:2009 172.27.86.172:2015 172.27.86.172:2019 & 
sleep(3)
python3 ./station-server.py BusportG 4013 2013 172.27.86.172:2005 172.27.86.172:2019 & 
sleep(3)
python3 ./station-server.py StationH 4015 2015 172.27.86.172:2001 172.27.86.172:2003 172.27.86.172:2009 172.27.86.172:2011 172.27.86.172:2019 & 
sleep(3)
python3 ./station-server.py TerminalI 4017 2017 172.27.86.172:2005 172.27.86.172:2019 & 
sleep(3)
python3 ./station-server.py JunctionJ 4019 2019 172.27.86.172:2011 172.27.86.172:2013 172.27.86.172:2015 172.27.86.172:2017
sleep(3)
