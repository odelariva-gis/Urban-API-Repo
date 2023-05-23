
'''
Utilies for serveral commonly used workflows for GraphQL Urban API. 
'''

import os
from typing import List
import sys
from arcgis.gis import GIS
import config
import importlib
import datetime
import time
from datetime import date
import math
import arcpy
from arcpy import geoprocessing
import sgqlc
from sgqlc.operation import Operation
from sgqlc.endpoint.http import HTTPEndpoint
from urban_api_schema import urban_api_schema as schema
import pandas as pd

importlib.reload(config)

def loggin_agol(config_name: str) -> GIS:
    '''
    Will log into AGOL for you! Must keep your 'config.py' file in the same location as your file. 

    Function return portal object of type GIS.  
    '''
    # Initialize/read config file
    cwd = sys.path[0]
    config_file = os.path.join(cwd, config_name)
    if not os.path.exists(config_file):
        print(f"Config file not found: {config_file}")
        sys.exit()
    else:
        print('Config File found and will continue!')

    # Getting login information
    username   = config.login_dict['username']
    pw         = config.login_dict['pw']
    portal_url = config.login_dict['portal_url']

    # Login to the portal...
    print(f'Login in as {username} into {portal_url}! Plese wait...')

    source = GIS(portal_url, username, pw)
    print(f'Success! Logged into {source} as {source.properties.user.username}!')

    return source

def create_token_header(config_name: str, gis_source: GIS = None) -> dict:
    '''
    This will function return the auth token string for GraphQL endpoint headers
    a type dict.  

    User can either provide a config.py file to input the token and have the function
    create the GraphQL header, or provide a GIS source of type GIS to provide the function. 
    This funciton will work in conjunction the function above, loggin_agol above, to provide a source
    of type GIS. 
    '''
    
    # Initialize/read config file
    cwd = sys.path[0]
    config_file = os.path.join(cwd, config_name)
    if not os.path.exists(config_file):
        print(f"Config file not found: {config_file}")
        sys.exit()
    else:
        print('Config File found and will continue!')

    token = ''

    if gis_source:
        print(f"Will get tokenf from the source GIS here: {gis_source}")
        token = gis_source._con.token
    else:
        print('Will get token from configure file...')
        token = config.login_dict['token']

    print(f'Creating your endpoint headers with this token: {token}...')

    endpoint_header = {'Authorization': 'Bearer ' + token}

    return endpoint_header

def request_token(gis_source: GIS) -> str:
    '''
    Returns token for user as type string.
    '''
    token = ''

    if gis_source:
        print(f"Will get tokenf from the source GIS here: {gis_source}")
        token = gis_source._con.token
    
    print('Here is your current token: ')
    print(token)

    return token

def return_unix_time(in_date: datetime.date) -> float:
    '''
    Function returns Unix time stamp.  Take in a tuple argument. 
    '''

    if in_date:
        return math.ceil(((time.mktime(in_date.timetuple()))))
    else:
        today_date = date.today()
        return math.ceil(((time.mktime(today_date.timetuple()))))
    

def get_fc_desc(in_fc: str, ) -> geoprocessing.gp:
    '''
    Returns a describe objects for input feature class 
    '''
    desc = arcpy.Describe(in_fc)

    return desc.ShapeFieldName + '@', desc.SpatialReference.factoryCode

def get_coords_plan(in_fc: str, shape_field:str ) -> List:
    '''
    '''
    coord_list = []

    with arcpy.da.SearchCursor(in_fc, [shape_field]) as cursor:
        temp_coord_list = []
        for row in cursor:
            coords = row[0]
            for part in coords:
                num_segs = len(part)
                print(f'Length of polygon is: {num_segs}')
                print('Iterating through the vertices...')

                for pnt in part:
                    if pnt:
                        temp_coord_list.append([pnt.X, pnt.Y])
    
        coord_list.append(temp_coord_list)
    
    del cursor

    print('Complete getting your plan boundary vertices...')

    return coord_list


def get_plan_dict(coord_list: List, 
                  event_name:str, 
                  end_date: float, 
                  start_date: float, 
                  planning_method: str, 
                  wkid: str) -> List:
    ''''
    
    '''

    geometry_dict = { 'rings': coord_list, 'spatialReference': {'wkid':wkid}}

    attributes_pre_dict = {
                        'EndDate': end_date,
                        'StartDate': start_date,
                        'EventName': event_name,
                        'PlanningMethod': planning_method                        
                    }

    attributes_dict = {'attributes': attributes_pre_dict, 'geometry': geometry_dict}

    return [attributes_dict]


def get_coords_parcels(in_fc: str, shape_field:str ) -> List:
    '''
    '''
    
    with arcpy.da.SearchCursor(in_fc, [shape_field]) as cursor:
        temp_coord_list = []
        for row in cursor:
            coords = row[0]
            for part in coords:
                num_segs = len(part)
                print(f'Length of polygon is: {num_segs}')
                print('Iterating through the vertices...')

                temp_vertex_list = []

                for pnt in part:
                    if pnt:
                        temp_vertex_list.append([pnt.X, pnt.Y])
                
            temp_coord_list.append(temp_vertex_list)
    
    del cursor

    print('Complete getting your plan boundary vertices...')

    return temp_coord_list
    #return coord_list


def get_parcel_dict(coord_list: List, 
                  custom_id:str,  
                  wkid: str) -> List:
    ''''
    Creates dictionary for adding parcels...
    '''

    geometry_dict = { 'rings': coord_list, 'spatialReference': {'wkid':wkid}}

    attributes_pre_dict = {
                        'custom_id': custom_id,                 
                    }

    attributes_dict = {'attributes': attributes_pre_dict, 'geometry': geometry_dict}

    return [attributes_dict]


def create_plans_from_fc(in_fc: str, 
                         event_name_field: str,
                         shape_field: str,
                        start_date_field: str,
                         end_date_field: str,
                         wkid: int,
                         title_database: str, 
                         urban_model_id: str,
                         endpoint: HTTPEndpoint)-> None:

    '''
    Creates initial urban design database
    '''
    
    ###Iterate through here...
    print('Complete getting your plan boundary vertices...')
   

    with arcpy.da.SearchCursor(in_fc, [shape_field, event_name_field,  start_date_field, end_date_field]) as cursor:
       
        for row in cursor:
            coord_list = []
            temp_coord_list = []
            coords = row[0]
            for part in coords:
                num_segs = len(part)
                print(f'Length of polygon is: {num_segs}')
                print('Iterating through the vertices...')

                for pnt in part:
                    if pnt:
                        temp_coord_list.append([pnt.X, pnt.Y])
    
            coord_list.append(temp_coord_list)

            print("Completed getting plan boundary vertices...")

            print(coord_list)
            print(" ")
    
            print("Creating Mutation schema...")
            ### Create mutation operation objects here...
            op = Operation(schema.Mutation)

            print("Creating new Urban Database Design...")
            create_urban_design_database = op.create_urban_design_database(
                                        urban_model_id = urban_model_id,
                                        title          = title_database + "_" + row[1]
                                        )
            
            print('*'*50)
            print(create_urban_design_database)
            
            
            json_data = endpoint(op)
            errors = json_data.get('error')

            print(json_data)
            print('*'*50)

            if errors:
                print(errors)
            else:
                print(f'Successfully created {title_database} as a design database...')

            ### Create new OP object ot better manage data that was created
            op_return = op + json_data

            ### Get the ID of the creation of the new urban design database
            op_database_id = op_return.create_urban_design_database
            print(f'Current Urban Design Datbase ID: {op_database_id}')

            _e_date = return_unix_time(row[3])
            _s_date = return_unix_time(row[2])
            print(f'Current Start Date: {_s_date}')
            print(f'Current End Date: {_e_date}')

            print(f"Creating  plan for {row[1]} plan boundary......")
    
            print("Creating plan GraphQL dictionary...")
            plan = get_plan_dict(coord_list, row[1], _e_date, _s_date, 'Zoning', 102100 )
            
            
            print('Here is your plan dictionary for plan creation...')
            print(plan)
            print(' ')
            
            print("Create Plan Mutations here...")
            
            ### Create the plan here
            op_create_plans = Operation(schema.Mutation)

            #urban model, urban_model_database, urban_data_model_view

            create_plans = op_create_plans.create_plans(
                    urban_database_id    = op_database_id,
                    plans                = plan
            )

            print('*'*50)
            print(create_plans)
            
        
            print("Inject JSON into GraphQL database...")
            json_data_plans = endpoint(op_create_plans)

            print(json_data_plans)
            print('*'*50)

            errors = json_data_plans.get('errors')
            if errors:
                print(errors)
            else:
                print(f'Successfully created {row[1]} as a new plan for Urban Model {urban_model_id} and Urban Design Database {op_database_id}...')
            
            op_return_plan_id = op_create_plans + json_data_plans
            created_plan_id = op_return_plan_id[0].attributes.global_id
            print(f'Newly created {row[1]} plan has a GlobalID of {created_plan_id}...')
            
            print("Created plan here...")
            print("="*50)
            print(' ')

            del coord_list, op, op_create_plans, op_database_id, op_return, json_data, json_data_plans, plan
            
        del cursor

        print('Finished creating plans. Existing tool now...')

        return None
    


def return_created_urban_design_database_id(op: schema.Mutation, json_data: HTTPEndpoint) -> str:
    '''
    
    '''
    ### Create new OP object ot better manage data that was created
    op_return = op + json_data

    ### Get the ID of the creation of the new urban design database
    op_database_id = op_return.create_urban_design_databse
    print(f'Current Urban Design Datbase ID: {op_database_id}')

    return op_database_id

def get_plan_paths(csv_path: str) -> pd.core.frame.DataFrame:
    '''
    '''

    df = pd.read_csv(csv_path)

    return df


def create_multiple_plans(df: pd.core.frame.DataFrame, 
                 urban_model_id: str, 
                 endpoint: HTTPEndpoint, 
                 urban_database_id: str, 
                 ) -> None:
    '''
    Tool will itereate through list of plans and intakes arguments for end and start date here...
    '''

    for index, _row in df.iterrows():

        plan  = _row['PLAN_PATH']
        event_name = _row['EVENT_NAME']
        _s_date_y = _row['START_DATE_Y']
        _s_date_m = _row['START_DATE_M']
        _s_date_d = _row['START_DATE_D']
        _e_date_y = _row['END_DATE_Y']
        _e_date_m = _row['END_DATE_M']
        _e_date_d = _row['END_DATE_D']
        
        _e_date = return_unix_time(_s_date_y, _s_date_m, _s_date_d)
        _s_date = return_unix_time(_e_date_y, _e_date_m, _e_date_d)

        print(f"Creating  plan for feature class: {plan}...")
        
        print("Creating shape field and WKID for plan...")
        shape_field, wkid = get_fc_desc(plan)

        print(f'Shape field: {shape_field}')
        print(f'WKID: {wkid}')
        
        print('Creating coordinates for plan...')
        coord = get_coords(plan, shape_field)
        
        print("Creating plan GraphQL dictionary...")
        print(f"Creating current plan name: {event_name}")
        plans = get_plan_dict(coord, event_name, _e_date, _s_date, 'Zoning', wkid )
        
        print("Create Mutations here...")
        
        ### Create the plan here
        op_create_plans = Operation(schema.Mutation)

        #urban model, urban_model_database, urban_data_model_view

        create_plans = op_create_plans.create_plans(
             urban_database_id    = urban_database_id,
             plans                = plans
        )

        print("Inject JSON into GraphQL database...")
        json_data = endpoint(op_create_plans)
        errors = json_data.get('errors')
        if errors:
            print(errors)
        else:
            print(f'Successfully created {event_name} as a new plan for urban model {urban_model_id} and urban design database {urban_database_id}...')
        print("="*50)
        print(' ')
        
    print("Completed script...")
    return None


def create_endpoint(graph_url: str, _auth:str) -> HTTPEndpoint:
    '''
    Creates endpoing for use in Urban API
    '''

    return(HTTPEndpoint( graph_url, _auth))
