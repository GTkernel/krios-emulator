import os
from sgp4.api import Satrec, jday
from latency import get_rtt
from utils import geodetic2cartesian, calculate_distance

# static function to get the network device name
network_device = "eno1"
	

def add_latency(time, ip_address, client, l1, l2):
	x,y,z = geodetic2cartesian(client[0], client[1], 550000)
	jd, fr = jday(time.year, time.month, time.day, time.hour, time.minute, time.second)
	satellite = Satrec.twoline2rv(l1, l2)
	e, location, velocity = satellite.sgp4(jd, fr)
	
	return add_latency_(ip_address, (x,y,z), location)
	

def add_latency_(ip_address, client, location):	
	distance = calculate_distance(client, location)
	rtt = get_rtt(distance)
	return __add_latency__(rtt, ip_address)
	


def __add_latency__(rtt, ip_address):
	# command = "tcset ens3 --delay " +  str(rtt) + "ms --network " + ip_address + " --overwrite"
	command = f"tcset {network_device} --delay {rtt}ms --network {ip_address} --overwrite"

	os.system(command)

	return rtt

