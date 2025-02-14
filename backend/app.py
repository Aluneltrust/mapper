from flask import Flask, request, jsonify
from flask_cors import CORS
import polyline
import requests
from shapely.geometry import LineString, shape, Point
from math import sin, cos, sqrt, atan2, radians

import json
import os
import logging
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# from data import state_boundaries, state_abbr


state_abbr = {
    'Arizona': 'AZ', 'Alabama': 'AL', 'Alaska': 'AK', 'Arkansas': 'AR', 
    'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 
    'Delaware': 'DE', 'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI', 
    'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 
    'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 
    'Maryland': 'MD', 'Massachusetts': 'MA', 'Michigan': 'MI', 
    'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO', 
    'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV', 
    'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 
    'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 
    'Ohio': 'OH', 'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 
    'Rhode Island': 'RI', 'South Carolina': 'SC', 'South Dakota': 'SD', 
    'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT', 
    'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV', 
    'Wisconsin': 'WI', 'Wyoming': 'WY',
    'District of Columbia': 'DC', 'Puerto Rico': 'PR'
}



def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth specified in decimal degrees
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    # Radius of earth in miles (IFTA standard)
    R = 3959.87433
    
    # Calculate distance and apply road adjustment factor
    distance = R * c
    road_adjustment = 1.02  # Account for road curves vs straight-line distance
    
    return distance * road_adjustment


# Load state boundary data
try:
    with open('data/state_boundaries.geojson') as f:
        state_boundaries = json.load(f)
    logger.info("Successfully loaded state boundaries")
except Exception as e:
    logger.error(f"Error loading state boundaries: {e}")
    state_boundaries = None

def get_detailed_route(origin, destination, waypoints, api_key):
    """Get detailed route from Google Maps API"""
    try:
        # Request detailed path with higher resolution
        url = 'https://maps.googleapis.com/maps/api/directions/json'
        params = {
            'origin': origin,
            'destination': destination,
            'waypoints': '|'.join(waypoints) if waypoints else '',
            'key': api_key,
            # Request more detailed route path
            'units': 'imperial',
            'alternatives': 'false'
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting route from Google Maps: {e}")
        raise




def get_state_distances(route_points, total_google_distance=None):
    """Calculate distance traveled in each state"""
    try:
        # Define state abbreviations dictionary within function scope
        state_abbrs = {
            'Arizona': 'AZ', 'Alabama': 'AL', 'Alaska': 'AK', 'Arkansas': 'AR', 
            'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 
            'Delaware': 'DE', 'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI', 
            'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 
            'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 
            'Maryland': 'MD', 'Massachusetts': 'MA', 'Michigan': 'MI', 
            'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO', 
            'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV', 
            'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 
            'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 
            'Ohio': 'OH', 'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 
            'Rhode Island': 'RI', 'South Carolina': 'SC', 'South Dakota': 'SD', 
            'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT', 
            'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV', 
            'Wisconsin': 'WI', 'Wyoming': 'WY',
            'District of Columbia': 'DC', 'Puerto Rico': 'PR'
        }

        state_distances = {}
        route = LineString(route_points)
        
        # Process each state the route goes through
        for feature in state_boundaries['features']:
            state_name = feature['properties']['NAME']
            state_abbr = state_abbrs.get(state_name)  # Use local dictionary
            
            if not state_abbr:
                continue

            state_polygon = shape(feature['geometry'])
            
            if route.intersects(state_polygon):
                state_section = route.intersection(state_polygon)
                distance = calculate_distance_in_miles(state_section)
                
                if distance > 0.1:
                    state_distances[state_abbr] = round(distance, 1)
                    print(f"Distance in {state_abbr}: {distance} miles")

        print("Pre-adjustment distances:", state_distances)
        
        if total_google_distance and sum(state_distances.values()) > 0:
            adjustment = total_google_distance / sum(state_distances.values())
            state_distances = {
                state: round(dist * adjustment, 1)
                for state, dist in state_distances.items()
            }
            
        return state_distances

    except Exception as e:
        print(f"Error: {str(e)}")
        raise

def calculate_distance_in_miles(line):
    """Calculate actual highway distance"""
    try:
        total_distance = 0
        coords = list(line.coords)
        
        for i in range(len(coords)-1):
            lon1, lat1 = coords[i]
            lon2, lat2 = coords[i+1]
            
            # Calculate great circle distance
            base_distance = haversine_distance(lat1, lon1, lat2, lon2)
            
            # Apply highway correction factor
            # Highways aren't straight lines between points
            highway_factor = 1.02  # PC*Miler typically uses something similar
            total_distance += base_distance * highway_factor
        
        return total_distance
    except Exception as e:
        print(f"Error calculating distance: {e}")
        return 0



@app.route('/api/calculate-route', methods=['POST'])
def calculate_route():
    try:
        data = request.json
        print(f"Received data: {data.keys()}")
        
        if 'route_details' not in data:
            return jsonify({'error': 'No route details provided'}), 400

        # Extract route points
        route_points = [(point['lng'], point['lat']) for point in data['route_details']]
        print(f"Extracted {len(route_points)} route points")
        
        # Calculate distances per state - pass the total_google_distance if available
        state_distances = get_state_distances(route_points, data.get('total_google_distance'))
        
        # No need for adjustment here since it's handled in get_state_distances
        return jsonify({
            'state_distances': state_distances,
            'total_distance': sum(state_distances.values())
        })

    except Exception as e:
        print(f"Error processing route: {e}")
        return jsonify({'error': str(e)}), 500
    
if __name__ == '__main__':
    app.run(debug=True)