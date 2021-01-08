from __future__ import division
from __future__ import print_function

from flask import Flask, jsonify, request, render_template

import pandas as pd

import requests
import json
import urllib

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

app = Flask(__name__)
 

@app.route('/', methods=['GET'])
def index():
    # return jsonify({'hello': 'Hi Buddy'}), 200
    return render_template('index.html')


def send_request(origin_addresses, dest_addresses, API_key):
    """ Build and send request for the given origin and destination addresses."""
    def build_address_str(addresses):
        # Build a pipe-separated string of addresses
        address_str = ''
        for i in range(len(addresses) - 1):
            address_str += addresses[i] + '|'
        address_str += addresses[-1]
        return address_str

    request            = 'https://maps.googleapis.com/maps/api/distancematrix/json?units=imperial'
    origin_address_str = build_address_str(origin_addresses)
    dest_address_str   = build_address_str(dest_addresses)
    request            = request + '&origins=' + origin_address_str + '&destinations=' + dest_address_str + '&key=' + API_key
    # print('request',request)
    # print('')
    jsonResult         = urllib.request.urlopen(request).read()
    response           = json.loads(jsonResult)
    return response


def build_distance_matrix(response):
    distance_matrix = []
    for row in response['rows']:
        row_list = [row['elements'][j]['distance']['value'] for j in range(len(row['elements']))]
        distance_matrix.append(row_list)
    return distance_matrix


def get_routes(solution, routing, manager):
    """Get vehicle routes from a solution and store them in an array."""
    # Get vehicle routes and store them in a two dimensional array whose
    # i,j entry is the jth location visited by vehicle i along its route.
    routes = []
    for route_nbr in range(routing.vehicles()):
        index = routing.Start(route_nbr)
        route = [manager.IndexToNode(index)]
        while not routing.IsEnd(index):
          index = solution.Value(routing.NextVar(index))
          route.append(manager.IndexToNode(index))
        routes.append(route)
    return routes



@app.route('/proses', methods=['POST'])
def proses():
    print(request.json)
    print(request.json.get('coord'))

    d = {'coord': request.json.get('coord')}
    df = pd.DataFrame(data=d)

    addresses = request.json.get('coord')
    API_key   = "AIzaSyCp1MSl1nQQEafWmunZ-11UFrfpftw_UgQ"


    # Distance Matrix API only accepts 100 elements per request, so get rows in multiple requests.
    max_elements    = 100
    num_addresses   = len(addresses) # 16 in this example.  
    # Maximum number of rows that can be computed per request (6 in this example).
    max_rows        = max_elements // num_addresses
      
    # num_addresses = q * max_rows + r (q = 2 and r = 4 in this example).
    q, r            = divmod(num_addresses, max_rows)
    dest_addresses  = addresses
      
    distance_matrix = []
    # Send q requests, returning max_rows rows per request.
    for i in range(q):
        origin_addresses = addresses[i * max_rows: (i + 1) * max_rows]
        response         = send_request(origin_addresses, dest_addresses, API_key)
        distance_matrix += build_distance_matrix(response)

    # Get the remaining remaining r rows, if necessary.
    if r > 0:
        origin_addresses = addresses[q * max_rows: q * max_rows + r]
        response         = send_request(origin_addresses, dest_addresses, API_key)
        distance_matrix += build_distance_matrix(response)

    # pp = pprint.PrettyPrinter(indent=3, width=1000, depth=2,compact=False)
    # pp.pprint(distance_matrix)

    distance_matrix = distance_matrix
    num_vehicles    = 1
    depot           = 0

    # Create the routing index manager.
    manager = pywrapcp.RoutingIndexManager(len(distance_matrix),num_vehicles,depot)
    # Create Routing Model.
    routing = pywrapcp.RoutingModel(manager)


    def distance_callback(from_index, to_index):
        """Returns the distance between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return distance_matrix[from_node][to_node]


    transit_callback_index = routing.RegisterTransitCallback(distance_callback)

    # Define cost of each arc.
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Setting first solution heuristic.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

    # Solve the problem.
    solution = routing.SolveWithParameters(search_parameters)

    if solution:
        routes = get_routes(solution, routing, manager)
        for i, route in enumerate(routes):
            print('Route', i, route)

        route_from  = route[:-1]
        route_to    = route
        route_to.sort()
        route_to    = route_to[2:]
        route_to.append(0)
        
        
    # print(distance_matrix)

    print(route_from)
    # df['from']  = route_from
    # df          = df.sort_values(by=['from'])
    # df['to']    = route_to
    # # print(df)
    
    print(route_to)
    # df_to   = df.drop(columns=['fc_branch','fc_custcode','custname','coord_list','to'])
    # df_to   = df_to.rename(columns={"lat": "lat_to","lng":"lng_to","from":"to"})
    # # print(df_to)

    # df    = df.join(df_to.set_index('to'), on='to')
    # # print(df)

    # return  jsonify({'df':df.to_json(orient='records')})

    df['urutan'] = route_from
    df['no']     = df.index

    print(df)
    


    return jsonify({
            'coord': request.json.get('coord'),
            'distance_matrix': distance_matrix,
            'df'        : df.to_json(orient='records')
        }), 200
    

if __name__ == '__main__':
    app.run(debug=True)