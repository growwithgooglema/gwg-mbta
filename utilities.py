#!/usr/bin/env python3
"""
Distance calculation functions for MBTAccess app
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
import argparse
import json
import os
import urllib.request as request
from argparse import RawDescriptionHelpFormatter
from math import asin, cos, pi, pow, sin, sqrt
from urllib.error import HTTPError


class BadUrlError(Exception):
    """Raise exception if given URL could not be opened"""
    pass


class MBTAResponseError(Exception):
    """Raise exception if MBTA returns an error"""
    pass


def get_distance(point1, point2):
    """
    Calculate distance between two points in kilometers with the Haversine formula.

    :type: dict
    :param: point1: dictionary with geolocation information
    :type: dict
    :param: point2: dictionary with geolocation information
    :rtype: float
    :return: Returns the distance (in kilometers) between point1 and point2
    """
    if point1 == point2:
        return 0
    earth_radius = 6372.8
    lat1 = to_radian(point1.get('lat'))
    lat2 = to_radian(point2.get('lat'))
    lon1 = to_radian(point1.get('lon'))
    lon2 = to_radian(point2.get('lon'))
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    sqrd_hcl = pow(sin(delta_lat/2), 2) + pow(sin(delta_lon/2), 2) * cos(lat1) * cos(lat2)
    angular_distance = 2 * asin(sqrt(sqrd_hcl)) * 100
    return (earth_radius * angular_distance) / 100


def to_radian(num):
    """
    Convert the given number's units to radian

    :type: float, int
    :param: num: Size of an angle
    :rtype: float
    :return: Returns the value, in radian, of num.
    """
    return (num * (pi / 180))


def get_stops(url):
    """
    Parse MBTA stop data data into a list of dictionaries.

    :type: string
    :param: url: currently, this value is https://api-v3.mbta.com/stops
    :rtype: list
    :return: Returns a list of dictionary objects.
    """
    rqst = request.Request(url)
    try:
        response = request.urlopen(rqst)
    except HTTPError:
        msg = "The provided URL {u} is not a correct MBTA data URL.".format(u=url)
        raise BadUrlError(msg) from None
    if response.status == 200:
        contents = response.read()
        if not isinstance(contents, str):
            contents = contents.decode('utf8')
        data = json.loads(contents)
        return data.get('data')
    msg = "The HTTP request to {u} failed with reason {r}."
    raise MBTAResponseError(msg.format(u=url, r=response.reason))


def process_schools(schools_data, url):
    """
    Calculate number of wheelchair-accessible and total stops for each school.

    type: str
    :param: schools_data: path to the school data json file
    :type: str
    :param: url: currently, this value is https://api-v3.mbta.com/stops
    """
    if not os.path.exists(schools_data):
        raise Exception("Can't process a file that does not exist.")
    with open(schools_data) as f:
        schools = json.load(f)
    stops = get_stops(url)
    new_schools = []
    for school in schools:
        if school.get('lat') and school.get('lng'):
            school['stops'] = 0
            school['wheelchairs'] = 0
            p1 = {'lat': school.get('lat'), 'lon': school.get('lng')}
            for stop in stops:
                attributes = stop.get('attributes')
                p2 = {'lat': attributes.get('latitude'), 'lon': attributes.get('longitude')}
                if get_distance(p1, p2) <= (1.609344)/2.0:
                    school['stops'] += 1
                    if attributes.get('wheelchair_boarding') > 0:
                        school['wheelchairs'] += 1
            if school['stops'] > 0:
                school['ratio'] = school['wheelchairs']/school['stops']
            else:
                school['ratio'] = 0
            new_schools.append(school)
    return json.dumps(new_schools)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("stops_url", help="URL to MBTA stops JSON data.")
    parser.add_argument("schools_data", help="Path to the JSON file containing universities data.")
    args = parser.parse_args()
    print(process_schools(args.schools_data, args.stops_url))
