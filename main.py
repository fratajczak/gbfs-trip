#!/usr/bin/env python3

import sys
from urllib.request import urlopen
import json
import time
from datetime import datetime, timezone
import math
import bisect


def new_trip(start_station, end_station, started_at, ended_at):
    """Create a trip dict used for json dump"""
    trip = dict()
    trip["started_at"] = datetime.fromtimestamp(started_at, tz=timezone.utc).isoformat(sep=" ")
    trip["ended_at"] = datetime.fromtimestamp(ended_at, tz=timezone.utc).isoformat(sep=" ")
    trip["duration"] = ended_at - started_at
    trip["start_station_id"] = start_station.id
    trip["start_station_name"] = start_station.name
    trip["start_station_latitude"] = start_station.lat
    trip["start_station_longitude"] = start_station.lon
    trip["end_station_id"] = end_station.id
    trip["end_station_name"] = end_station.name
    trip["end_station_latitude"] = end_station.lat
    trip["end_station_longitude"] = end_station.lon
    return trip


class Station:
    """Represents a station, created from a json entry"""

    def __init__(self, station_json):
        self.id = station_json["station_id"]
        self.name = station_json["name"]
        self.lat = station_json["lat"]
        self.lon = station_json["lon"]

    def __lt__(self, other):
        return self.lon < other.lon


class Bike:
    """Represents a bike, created from a json entry"""

    def __init__(self, bike_json, last_seen_at):
        self.lat = bike_json["lat"]
        self.lon = bike_json["lon"]
        self.last_seen = last_seen_at

    def __lt__(self, other):
        return self.lon < other.lon

    def away_from(self, other):
        """Returns true if the other object is more than 50 meters away
        in order to account for GPS inaccuracy
        """
        return distance(self, other) > 50

    def has_moved(self, other):
        """Returns true if self has different coordinates from other"""
        return self.lat != other.lat or self.lon != other.lon

    def find_station(self, station_list):
        """finds a station less than 10 meters away from the bike in a
        sorted station list using binary search
        if there is none (flex parking), return a special station
        """
        i1 = bisect.bisect_left(station_list, self)
        i2 = bisect.bisect_right(station_list, self)
        d1 = distance(station_list[i1], self) if i1 is not None else float("inf")
        d2 = distance(station_list[i2], self) if i2 is not None else float("inf")
        if d1 < d2 and d1 < 10:
            return station_list[i1]
        if d2 < 10:
            return station_list[i2]
        station = dict()
        station["station_id"] = 0
        station["name"] = "Flex parking"
        station["lat"] = self.lat
        station["lon"] = self.lon
        return Station(station)


def distance(obj1, obj2):
    """Calculate distance in meters using spherical Earth projected to a plane:
    fine for small distances, fast
    object must have a lat and lon attribute
    """
    lat1 = math.radians(obj1.lat)
    lat2 = math.radians(obj2.lat)
    del_lat = lat2 - lat1
    del_lon = math.radians(obj2.lon - obj1.lon)
    mean_lat = (lat1 + lat2) / 2
    r = 6371e3
    return r * math.sqrt(del_lat ** 2 + (math.cos(mean_lat) * del_lon) ** 2)


class BikeRegistry:
    """Describes the entire context around free bikes and logs bikes
    in order to detect bikes that were moved during trips, also logs trips
    """

    def __init__(self, city_name, station_info_url, free_bike_status_url):
        self.city_name = city_name
        self.free_bike_status_url = free_bike_status_url
        self.bikes = dict()
        self.ttl = None
        self.last_updated = None
        self.trips = []
        try:
            data = urlopen(station_info_url)
            stations_json = json.load(data)["data"]["stations"]
        except (IOError, json.decoder.JSONDecodeError):
            sys.exit("Could not load station info json, exiting...")
        # can't use a hash map because bike coordinates aren't exactly equal
        # to station coordinates, so we use a sorted array
        self.stations = []
        for station_json in stations_json:
            self.stations.append(Station(station_json))
        self.stations.sort()

    def update(self):
        """Get free_bike_status.json then compare and update the status of
        free bikes, detect if a trip happenned and if so, log it
        Doesn't cover the edge case of a trip from one station to the same one
        This would require us to also check if a bike disappears from the json,
        which is slower and the edge case probably doesn't happen very often
        """
        try:
            data = urlopen(self.free_bike_status_url)
            free_bike_status_json = json.load(data)
        except (IOError, json.decoder.JSONDecodeError):
            print("Could not load json, retrying in 1 second...")
            return
        if free_bike_status_json["last_updated"] == self.last_updated:
            return
        self.last_updated = free_bike_status_json["last_updated"]
        self.ttl = free_bike_status_json["ttl"]

        bikes_json = free_bike_status_json["data"]["bikes"]
        for bike_json in bikes_json:
            bike_id = bike_json["bike_id"]
            cur_bike = Bike(bike_json, self.last_updated)
            if bike_id in self.bikes:
                old_bike = self.bikes[bike_id]
                # ignore trips of less than 100 seconds (moved by mistake/cancelled)
                if old_bike.away_from(cur_bike) and self.last_updated - old_bike.last_seen > 100:
                    print("New trip added")
                    start_station = old_bike.find_station(self.stations)
                    end_station = cur_bike.find_station(self.stations)
                    self.trips.append(
                        new_trip(
                            start_station,
                            end_station,
                            old_bike.last_seen,
                            self.last_updated,
                        )
                    )
                    self.bikes[bike_id] = cur_bike
                else:
                    self.bikes[bike_id].last_seen = self.last_updated
                    if old_bike.has_moved(cur_bike):  # update position if moved a bit
                        self.bikes[bike_id] = cur_bike
            elif bike_json["is_disabled"] == 0:
                self.bikes[bike_id] = cur_bike

        print("updated", self.city_name, "at", datetime.now().isoformat(sep=" "))


if __name__ == "__main__":
    berlin_bikes = BikeRegistry(
        "Berlin",
        "https://gbfs.nextbike.net/maps/gbfs/v1/nextbike_bn/de/station_information.json",
        "https://gbfs.nextbike.net/maps/gbfs/v1/nextbike_bn/de/free_bike_status.json",
    )
    try:
        while True:
            berlin_bikes.update()
            # wait until end of ttl
            now = time.time()
            if berlin_bikes.last_updated + berlin_bikes.ttl > now:
                time.sleep(berlin_bikes.last_updated + berlin_bikes.ttl - now)
            # wait 1 second in case of update delays or timesync issues
            time.sleep(1)
    except KeyboardInterrupt:
        berlin_bikes.trips.sort(key=lambda k: k['started_at'])
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(berlin_bikes.trips, f, ensure_ascii=False, indent=4)
