from utils import read_tles, haversine_distance, geodetic2cartesian, calculate_distance
from latency import *
from datetime import datetime
from tc_commands import add_latency, add_latency_, __add_latency__
import pycurl
import socket
import json
import time
from sgp4.api import Satrec, jday
import numpy as np
from copy import deepcopy

satellites = read_tles("tles.txt")

ip_mapping = cloudlab_fetch_ip_mapping()

client_location = (37.7749, -122.4194) #SF
lon_extremes = (-123.555907, -121.282894)
lat_extremes = (36.8765844341946, 38.67321556580541)
radius = 100

def generate_multiple_client_locations(center=client_location, app_radius = 100):
    clients = []
    clients.append(geodetic2cartesian(center[0], center[1], 550000))
    r = 0.01
    num_points = 10
    max_distance = 0
    while True:
        current_points = []
        for theta in list(np.linspace(0, 2*np.pi, num=int(num_points), endpoint=False)):
            new_lat = center[0] + r * np.cos(theta)
            new_lon = center[1] + r * np.sin(theta)
            point = geodetic2cartesian(new_lat, new_lon, 550000)
            current_points.append(np.array(point))
            dist = haversine_distance((new_lat, new_lon), center)
            if dist > max_distance:
                max_distance = dist

        if max_distance > app_radius:
            break

        clients += current_points        
        num_points += 10
        r += 0.01

    return np.array(clients)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host = ''
port = 12444
clients = generate_multiple_client_locations(client_location, radius)
print(clients.shape)
s.bind((host,port))
s.listen(10)

latencies = []
rtts = []


i = 0
conn, addr = s.accept()
prev_node = None
prev_rtt = 0
with conn:
    data = conn.recv(1024)
    data = data.decode()
    print(data)
    t = float(data) + 5

    while True:
        data = conn.recv(1024)
        if not data:
            continue

        data = data.decode()
        print(data)
        if data == "exit":
            break
        
        x = data.split("_")
        node = x[0]
        sat_mapping = json.loads(x[1])

        satellite = satellites[sat_mapping[node]]
        t = time.time()
        tt = datetime.fromtimestamp(t)
        jd, fr = jday(tt.year, tt.month, tt.day, tt.hour, tt.minute, tt.second)
        sat = Satrec.twoline2rv(satellite['line1'], satellite['line2'])
        e, location, velocity = sat.sgp4(jd, fr)
        location = np.array(location)
        distances_to_satellite = np.sqrt(np.sum((clients - location) ** 2, axis=-1))
        farthest_client_id = np.argmax(distances_to_satellite)

        farthest_distance = distances_to_satellite[farthest_client_id]
        rtt = get_rtt(farthest_distance)
        prev_rtt = __add_latency__(rtt, ip_mapping[node])
            
        rtts.append(prev_rtt)
        print(tt)
        curl_latencies = 0
        
        c = pycurl.Curl()
        url = "http://" + ip_mapping[node] + ":30163"
        c.setopt(c.URL, url)
        c.setopt(pycurl.WRITEFUNCTION, lambda x: None)
        c.setopt(pycurl.CONNECTTIMEOUT, 1)

        try:
            c.perform()
            c.perform()
            curl_latency = c.getinfo(pycurl.TOTAL_TIME)
            latencies.append(curl_latency)
            print(prev_rtt, c.getinfo(pycurl.TOTAL_TIME), c.getinfo(pycurl.NAMELOOKUP_TIME), c.getinfo(pycurl.CONNECT_TIME), c.getinfo(pycurl.PRETRANSFER_TIME), c.getinfo(pycurl.REDIRECT_TIME), c.getinfo(pycurl.STARTTRANSFER_TIME))
        except pycurl.error as e:
            print(e)

print(rtts)
print(latencies)

