#!/usr/bin/env python
import s2sphere
from s2sphere import CellId, math
import os
import sys
import json
import time
import pprint
import logging
import getpass
import argparse
from mock_pgoapi import mock_pgoapi as pgoapi

log = logging.getLogger(__name__)

def break_down_area_to_cell(north, south, west, east):
	""" Return a list of s2 cell id """
	result = []
		
	region = s2sphere.RegionCoverer()
	# set min_level and max_level to the same, to make sure we have cells of same size.
	region.min_level = 15
	region_max_level = 15
	# generate 2 points to finalize the area.
	p1 = s2sphere.LatLng.from_degrees(north, west)
	p2 = s2sphere.LatLng.from_degrees(south, east)

	#transform 2points into latitude and longtitude to finalize an area, and generating cells, return cells' ids.
	cell_ids = region.get_covering(s2sphere.LatLngRect.from_point_pair(p1,p2))
	result += [ cell_id.id() for cell_id in cell_ids ]
	print "cell_ids", result
	return result

#get latitude and longtitude positin of a cell_id
def get_position_from_cell_id(cellid):
	cell = CellId(id_ = cellid).to_lat_lng()
	return (math.degrees(cell._LatLng__coords[0]), math.degrees(cell._LatLng__coords[1]), 0)

def search_point(cell_id, api):
	# Parse position
	position = get_position_from_cell_id(cell_id)

	# Set player position on the earth
	api.set_position(*position)

	# Print get_maps_object
	cell_ids = [ cell_id ]
	timestamps = [0]
	response_dict = api.get_map_objects(latitude =position[0],
						longitude = position[1],
						since_timestamp_ms = timestamps,
						cell_id = cell_ids)

	return response_dict

def parse_pokemon(search_response):
	map_cells = search_response["responses"]["GET_MAP_OBJECTS"]["map_cells"]
	print "map_cells:", map_cells
	map_cell = map_cells[0]
	print "map_cell:~~~~", map_cell
	catchable_pokemons = map_cell["catchable_pokemons"]
	print "~~~ catchable pokemons", catchable_pokemons

	return catchable_pokemons

def scan_area(north, south, west, east, api):
	result = []
	# 1.Find all point to search with the area
	cell_ids = break_down_area_to_cell(north, south, west, east)
	# 2. Search each point, get result from api
	for cell_id in cell_ids:
		search_response = search_point(cell_id, api)
		# 3. Parse pokemon info
		pokemons = parse_pokemon(search_response)
		# 4. Aggregate pokemon info and return
		result += pokemons
	return result

def init_config():
	parser = argparse.ArgumentParser()
	config_file = "config.json"

	# If config file exists, load variables from json
	load = {}
	if os.path.isfile(config_file):
		with open(config_file) as data:
			load.update(json.load(data))

	# Read passed in Arguments
	required = lambda x: not x in load
	parser.add_argument("-a", "--auth_service", help="Auth Service ('ptc' or 'google')",required=required("auth_service"))
	parser.add_argument("-u", "--username", help="Username", required=required("username"))
	parser.add_argument("-p", "--password", help="Password")
	parser.add_argument("-l", "--location", help="Location", required=required("location"))
	parser.add_argument("-d", "--debug", help="Debug Mode", action='store_true')
	parser.add_argument("-t", "--test", help="Only parse the specified location", action='store_true')
	parser.add_argument("-px", "--proxy", help="Specify a socks5 proxy url")
	parser.set_defaults(DEBUG=False, TEST=False)
	config = parser.parse_args()

	# Passed in arguments shoud trump
	for key in config.__dict__:
		if key in load and config.__dict__[key] == None:
			config.__dict__[key] = str(load[key])

	if config.__dict__["password"] is None:
		log.info("Secure Password Input (if there is no password prompt, use --password <pw>):")
		config.__dict__["password"] = getpass.getpass()

	if config.auth_service not in ['ptc', 'google']:
		log.error("Invalid Auth service specified! ('ptc' or 'google')")
		return None

	return config

def init_api(config):
	# Instantiate pgoapi
	api = pgoapi.PGoApi()
	api.set_proxy({'http': config.proxy, 'https': config.proxy})

	# new authentication initialitation
	if config.proxy:
		api.set_authentication(provider = config.auth_service,
							username = config.username, password = config.password, proxy_config = {'http': config.proxy, 'https': config.proxy})
	else:
		api.set_authentication(provider = config.auth_service, username = config.username, password = config.password)
	# provide the path for your encrypt dll
	api.activate_signature("/home/ubuntu/pgoapi/libencrypt.so")

	return api


if __name__ == "__main__":
	config = init_config()
	api = init_api(config)


	#Point 1: 40.7665138, -74.0003176
	#Point 2: 40.7473342, -73.987956
	print "mypokemon_api scan_area:", scan_area(40.7665138,40.7473342,-74.0003176, -73.487958, api)
