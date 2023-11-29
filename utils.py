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



def funciton_timer(in_function)->str:

    '''
    Function wrapper to time other functions...
    '''

    def wrap_function(*args, **kwargs):
        t1= time()
        result = in_function(*args, **kwargs)
        t2 = time()
        print(f'Function {in_function.__name__!r} executed in {(t2-t1):.4f}s')
        return result
    return wrap_function



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

    print(f'Creating your endpoint headers with token...')
    print(" ")

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



def return_unix_time(in_date: datetime.date = None) -> float:

    '''
    Function returns Unix time stamp.  Take in a tuple argument. 
    '''

    if in_date:
        return math.ceil(((time.mktime(in_date.timetuple())))) * 1000
    else:
        today_date = date.today()
        return math.ceil(((time.mktime(today_date.timetuple())))) * 1000
    


def get_fc_desc(in_fc: str, ) -> geoprocessing.gp:

    '''
    Returns a describe objects for input feature class 
    '''

    desc = arcpy.Describe(in_fc)

    return desc.ShapeFieldName + '@', desc.SpatialReference.factoryCode



def create_endpoint(graph_url: str, _auth:str) -> HTTPEndpoint:

    '''
    Creates endpoing for use in Urban API
    '''

    print('Created Endpoint successfully...')

    return(HTTPEndpoint( graph_url, _auth))

def create_database(urban_model_id: str, title: str, endpoint: HTTPEndpoint) -> str:
    '''
    Creates a single urban database for the testing of projects or plans into a fresh GDB. 
    '''
    op = Operation(schema.Mutation)

    create_urban_design_database = op.create_urban_design_database(
                                            urban_model_id = urban_model_id,
                                            title          = title
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
        print(f'Successfully created as a design database...')

    ### Create new OP object ot better manage data that was created
    op_return = op + json_data

    ### Get the ID of the creation of the new urban design database
    op_database_id = op_return.create_urban_design_database
    print(f"Here is the ID for your newly created Urban Database: {op_database_id}")

    return op_database_id


def get_coords_plan(in_fc: str, shape_field:str ) -> List:

    '''
    Gets your coordinate from your plans input as a feature class...
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
    Creates a list of dicitonary of coords and events and dates from the feature class.  
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
    Gets coordinates from the feature class for plans being input.  
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
                         endpoint: HTTPEndpoint)-> dict:

    '''
    Creates initial urban design database
    '''
    
    ###Iterate through here...
    print('Complete getting your plan boundary vertices...')
   
    global_id_list = {}

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

            print("Inject JSON into GraphQL database...")
            json_data_plans = endpoint(op_create_plans)

            print('*'*50)

            errors = json_data_plans.get('errors')
            if errors:
                print(errors)
            else:
                print(f'Successfully created {row[1]} as a new plan for Urban Model {urban_model_id} and Urban Design Database {op_database_id}...')
            
            op_return_plan_id = op_create_plans + json_data_plans
            created_plan_id = op_return_plan_id.create_plans[0].attributes.global_id
            print(f'Newly created {row[1]} plan has a GlobalID of {created_plan_id}...')

            global_id_list[op_database_id] =  created_plan_id
            
            print("Created plan here...")
            print("="*50)
            print(' ')

            del coord_list, op, op_create_plans, op_database_id, op_return, json_data, json_data_plans, plan
            
        del cursor

        print('Finished creating plans. Existing tool now...')

        return global_id_list
    


def return_created_urban_design_database_id(op: schema.Mutation, json_data: HTTPEndpoint) -> str:

    '''
    Will return the database of the created ID with the OP mutation as an argument.  
    '''

    ### Create new OP object ot better manage data that was created
    op_return = op + json_data

    ### Get the ID of the creation of the new urban design database
    op_database_id = op_return.create_urban_design_databse
    print(f'Current Urban Design Datbase ID: {op_database_id}')

    return op_database_id



def create_branch_dict(
                       urban_event_id: str,
                       owner_name: str,
                       ) -> List:

    '''
    Creates dictionary/GraphQL query for creation of branches...
    '''

    attributes_existing = {
                        "branch_name": "Existing",
                        "branch_order": 1,
                        "existing": True,
                        "urban_event_id": urban_event_id,
                        "description": "existing conditions"
                    }
    
    single_branch_existing = {"attributes": attributes_existing}

    attributes_future = {
                        "branch_name": "Scenario 1",
                        "branch_order": 2, 
                        "owner_name": owner_name, 
                        "urban_event_id": urban_event_id, 
                        'existing': False, 
                        'description': 'the basic concept of the plan'
                        }

    single_branch_future = {"attributes": attributes_future}

    return [single_branch_existing, single_branch_future]



def inject_branch(branch_dict: dict, urban_database_id: str, endpoint: HTTPEndpoint)-> schema.Mutation:
    '''
    Output branches to iterate through, will output a list
    '''

    op = Operation(schema.Mutation)

    create_branch = op.create_branches(
                    urban_database_id = urban_database_id, 
                    branches = branch_dict
                    )
    
    print('Took in branch dictionary, will add to the the endpoint now...')

    print("Injecting JSON into GraphQL database...")

    json_data_plans_= endpoint(op)

    errors = json_data_plans_.get('errors')

    if errors:
        print(errors)
    else:
        print(f'Successfully created branches as a new plan for Urban Dabase ID {urban_database_id} ...')

    op_return_branch = op + json_data_plans_

    return op_return_branch



def inject_parcels(op_return_branch: schema.Mutation, 
                   urban_id: str, 
                   owner_: str, 
                   endpoint: HTTPEndpoint, 
                   urban_model_id: str,
                   urban_database_id: str,
                   wkid: int) -> None:

    '''
    Iterate through branches, create the Op to query, then itereate through urban databases to get parcel list, output will beparcel liss

    '''

    for branch in op_return_branch.create_branches:
        branch_id = branch.attributes.global_id

        print(f'Branch Name: {branch.attributes.branch_name}')
        print(f'Current Branch ID: {branch_id}')
        
        op_query_plan = Operation(schema.Query)

        query_plans = op_query_plan.urban_design_databases(owners = [owner_])
        query_plans.owner()
        query_plans.title()
        query_plans.id()
        query_plans.plans(filter = {"global_ids": [urban_id]})
        
        data_out = endpoint(op_query_plan)
        data_out

        op_return_geometry = op_query_plan + data_out

        
        for i in range(len(op_return_geometry.urban_design_databases)):
            if op_return_geometry.urban_design_databases[i].plans == []:
                pass
            else:
                
                overlay_coords = op_return_geometry.urban_design_databases[i].plans[0].geometry.rings
                geo_filter_dict = create_parcel_overlay(overlay_coords)
                
                op_query_parcels = Operation(schema.Query)
                query_parcels = op_query_parcels.urban_model(urban_model_id = urban_model_id)
                overlay_geometry = query_parcels.urban_database.parcels(geometry_filter = geo_filter_dict)
                
                parcel_data_out = endpoint(op_query_parcels)
                parcel_data_out
                
                ### create new query object to review data of the parcles that came out, should be 83 parcels in this example
                parcel_data_op = op_query_parcels + parcel_data_out
                
                ### research how to get the global id here
                print('Getting parcel information here...')
                
                parcel_list = get_parcel_list(parcel_data_op)
                
                print(f"My number of selected parcels for current Branch ID {branch_id} is currently: {len(parcel_list)}")

                add_multiple_parcels(parcel_list, urban_database_id, branch_id, wkid, endpoint)


                print(" ")

    return None


def create_parcel_overlay(coords: List) -> dict:

    '''
    Creates query for parcel overlay selection
    '''

    pre_dict = {'rings': coords, 'spatialReference': {'wkid': 102100}}

    overlay_dict = {'polygon': pre_dict, 'relationship': 'Contains'}

    return overlay_dict



def get_parcel_list(parcel_data_op: str)-> List:

    '''
    Will get coordinates from the returned data.
    '''

    parcel_list = []

    len_parcels = len(parcel_data_op.urban_model.urban_database.parcels)

    for parcel in range(len_parcels):
        temp_list = []
        temp_list.append(parcel_data_op.urban_model.urban_database.parcels[parcel].attributes.global_id)
        temp_list.append(parcel_data_op.urban_model.urban_database.parcels[parcel].attributes.custom_id)
        temp_list.append(parcel_data_op.urban_model.urban_database.parcels[parcel].attributes.geodetic_shape_area)
        temp_list.append(parcel_data_op.urban_model.urban_database.parcels[parcel].geometry.rings)
        parcel_list.append(temp_list)

    print('Finished getting coordinate from OP objects... ')

    return parcel_list



def create_add_parcel_dict(parcel_list: List, 
                           branch_id: str, 
                           wkid: int,) -> List:
        
    '''
    Create the dictionary for the add parcel to the model, needs to intake 1 sigle list, will not iterate through 
    the list of necessary items.  
    '''

    geometry_dict = {'rings': parcel_list[3], 'spatialReference': {'wkid': wkid} }

    attribute_pre_dict = {'BranchID': branch_id, 'CustomID': parcel_list[1], 'ShapeArea': parcel_list[2]}
   

    attribute_dict = {'attributes': attribute_pre_dict, 'geometry': geometry_dict}
    
    print(f"Successfuly created parcel dict for Branch ID: {branch_id}")
    return [attribute_dict]



def add_multiple_parcels(parcel_list: List, 
                         urban_database_id: str,
                         branch_id: str, 
                         wkid: int,
                         endpoint: HTTPEndpoint) -> None:
    
    '''
    Able to add multiple parcels by coord list, uses in conjuction with create_add_parcel_dict above. 
    This will iterate though the add parcel list for you and create the dictionary. 
    '''

    for parcel in parcel_list:
        add_parcel_dict = create_add_parcel_dict(parcel, branch_id, wkid)
        
        op_add_parcel = Operation(schema.Mutation)

        create_branch = op_add_parcel.create_parcels(
                    urban_database_id = urban_database_id,
                    parcels = add_parcel_dict
                    )
        

        print("Injecting Parcel JSON into GraphQL database...")
        json_data_parcel = endpoint(op_add_parcel)

        errors = json_data_parcel.get('errors')
        if errors:
            print(errors)
        else:
            print(f'Successfully created new parcel at Global ID: {parcel[0]}')

        del add_parcel_dict, op_add_parcel, create_branch, json_data_parcel

def create_project_dict(coord_list: List, 
                  event_name:str, 
                  start_date: float, 
                  end_date: float, 
                  address: str,
                  owner_: str,
                  status_: str,
                  wkid: str) -> List:
    
    ''''
    Creates a list of dicitonary of coords and events and dates from the feature class.  
    '''

    geometry_dict = { 'rings': coord_list, 'spatialReference': {'wkid':wkid}}

    attributes_pre_dict = {
                        'EndDate':   end_date,
                        'StartDate': start_date,
                        'EventName': event_name,
                        'Address':   address,
                        #'Status':    status_,
                        'OwnerName': owner_                  
                    }

    attributes_dict = {'attributes': attributes_pre_dict, 'geometry': geometry_dict}

    return [attributes_dict]

def create_project(project_dict: dict, urban_database_id: str, endpoint: HTTPEndpoint)-> schema.Mutation:
    '''
    Creates projection mutation schema...
    '''
    
    op_create_project = Operation(schema.Mutation)

    create_project = op_create_project.create_projects(
                        urban_database_id = urban_database_id,
                        projects = project_dict
                            )
    
    json_data_project= endpoint(op_create_project)

    errors = json_data_project.get('error')

    print(json_data_project)
    print('*'*50)

    if errors:
        print(errors)
    else:
        print(f'Successfully created a project...')

    op_project_return = op_create_project + json_data_project
    project_id = op_project_return.create_projects[0].attributes.global_id

    print(f"Project with ID: {project_id} has been created!")

    return project_id


def create_projects_from_fc(in_fc: str,
                       shape_field: str,
                       event_name_field: str,
                       start_date_field: str,
                       end_date_field: str,
                       address_field: str,
                       wkid: int, 
                       title_database: str,
                       urban_model_id: str, 
                       owner_: str,
                       status_field: str,
                       endpoint: HTTPEndpoint)-> dict:
    """
    This will inject projects...
    """
    
    ###Iterate through here...
    print('Complete getting your project boundary vertices...')
   
    project_id_list = {}

    with arcpy.da.SearchCursor(in_fc, [shape_field, event_name_field, start_date_field, end_date_field, status_field, address_field]) as cursor:
       
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

            print("Completed getting project boundary vertices...")

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

            ### Will need to return these ID's 
            print(f'Current Urban Design Datbase ID: {op_database_id}')

            _e_date = return_unix_time(row[3])
            _s_date = return_unix_time(row[2])
            print(f'Current Start Date: {_s_date}')
            print(f'Current End Date: {_e_date}')

            print(f"Creating project for {row[1]} project boundary......")

            print("Creating plan GraphQL dictionary...")
            project_dict = create_project_dict(coord_list, row[1], _s_date, _e_date, row[5], owner_, row[4], wkid )
            
            print('Here is your plan dictionary for project creation...')
            print(project_dict)
            print(' ')
        

            print("Create Project Mutations here...")

            created_project_id = create_project(project_dict, op_database_id, endpoint)

            project_branch = create_branch_dict(created_project_id, owner_)

            inject_branch(project_branch, op_database_id, endpoint)

            print(f"Completed creating project and appropriate branches for database ID: {op_database_id}")
            
            print("="*50)
            print(' ')

            del coord_list, op, create_urban_design_database, op_database_id, op_return, json_data, project_dict, created_project_id, project_branch
            
        del cursor

        print('Finished creating projects. Exiting tool now...')

    return project_id_list


def create_use_type_query(limit_: int, urban_model_id: int, endpoint: HTTPEndpoint)-> Operation:
    """
    This will create the query needed to get the Use Type values from the plans in a project.  
    """
    
    ### Create teh query here limited to plans.

    op = Operation(schema.Query)
    use_types = op.urban_design_databases(urban_model_id = urban_model_id, limit = limit_)

    use_types.plans.space_use_types.attributes.metric_parameters()
    use_types.plans.space_use_types.attributes.space_use_type_name()
    use_types.plans.attributes.event_name()
    use_types.plans.space_use_types.attributes.metric_parameters()
    use_types.plans.space_use_types.attributes.space_use_type_name()
    use_types.plans.attributes.event_name()
    use_types.plans.metric_sources()

    data_out = endpoint(op)
    data_out = op + data_out

    return data_out

def export_use_types(data_out: schema.Query, folder_path: str)->None:
    '''
    Export a CSV Per Plan with appropriate use types for each plan...
    '''

    len_plans = len(data_out.urban_design_databases)
    print(f"We currently have {len_plans} in this urban database...")
    csv_list = []
    headers_ = ['METRIC_ID', 'METRIC_VALUE', 'METRIC_NAME']
    for plan in range(len_plans):
        
        print(f"Currently on plan index: {plan}")
        
        if data_out.urban_design_databases[plan].plans == []:
            print("NO PLAN FOUND")
        elif data_out.urban_design_databases[plan].plans[0].space_use_types == []:
            print("NO USETYPES FOUND")
        else:
            plan_name = data_out.urban_design_databases[plan].plans[0].attributes.event_name
            output_file = plan_name + ' Metrics.csv'
            print(plan_name)
            len_sources = len(data_out.urban_design_databases[plan].plans[0].metric_sources)
            print(f"We have {len_sources} metric sources...")
            print("-"*50)
            
            id_dict = {}

            ### Creating 
            for x in range(len_sources):
                source_name = data_out.urban_design_databases[plan].plans[0].metric_sources[x].attributes.source_name
                source_metric_id = data_out.urban_design_databases[plan].plans[0].metric_sources[x].attributes.global_id
                weight_name = data_out.urban_design_databases[plan].plans[0].metric_sources[x].attributes.weight_name
                
                ### To print if necessary...
    #             print(f"SOURCE NAME: {source_name}")
    #             print(f"WEIGHT NAME: {weight_name}")
    #             print(f"SOURCE METRIC ID: {source_metric_id}")
    #             print(" ")
                
                #### Creating dictionary here from metric sources to use for metric parameters
                
                if source_name is None:
                    id_dict[source_metric_id] = str(weight_name)
                elif weight_name is None:
                    id_dict[source_metric_id] = str(source_name)
                else:
                    id_dict[source_metric_id] = str(source_name) + " " + str(weight_name)

              ### To print outstanding dictionary if necessary 
    #         for k in id_dict:
    #             print(f"{id_dict[k]} : {k}")
                
            ### Iterating through metric paramters here 
            len_metric_paramters = len(data_out.urban_design_databases[plan].plans[0].space_use_types[0].attributes.metric_parameters)
            for mp in range(len_metric_paramters):
                temp_csv_list = []
                temp_metric_id = data_out.urban_design_databases[plan].plans[0].space_use_types[0].attributes.metric_parameters[mp].metric_source_id
                metric_value   = data_out.urban_design_databases[plan].plans[0].space_use_types[0].attributes.metric_parameters[mp].value
                print(f"Metric ID: {temp_metric_id}")
                print(f"Metric Value: {metric_value}")
                temp_csv_list.append(temp_metric_id)
                temp_csv_list.append(metric_value)

                try:
                    print(f"Output: {id_dict[temp_metric_id]}")
                    temp_csv_list.append(id_dict[temp_metric_id])
                except:
                    print("No Value Found")
                    temp_csv_list.append('NO VALUE FOUND')
                
                csv_list.append(temp_csv_list)
                
                
            df = pd.DataFrame(csv_list, columns = headers_)

            output_path = os.path.join(folder_path, output_file)

            if os.path.exists(output_path):
                os.remove(output_path)
                print(f"Deleted file: {output_path}")

            df.to_csv(output_path, encoding='utf-8')
        
                                    
        print("-"*50)
        
    print("Done!")
    

def get_zone_type_count(urban_model_id: str, endpoint: HTTPEndpoint) -> str:
    '''
    Gets amount of zone types 
    '''
    op = Operation(schema.Query)

    urban_database = op.urban_model(
                                    urban_model_id = urban_model_id,
                                    )
    
    urban_database.urban_database.zone_types_meta.count()
                
    data_out = endpoint(op)
    data_out  = op + data_out

    json_data = endpoint(op)
    errors = json_data.get('error')

    if errors:
        print(errors)
    else:
        print(f'Successfully queried number of Zone Types...')
        print(" ")

    ### Get the ID of the creation of the new urban design database
    zone_type_count = data_out.urban_model.urban_database.zone_types_meta.count

    print(f"You have {zone_type_count} Zone Types ID's in the current Urban Model: {urban_model_id}.")

    return None

def get_zone_types(urban_model_id: str, endpoint: HTTPEndpoint) -> List: 
    '''
    Get zones types and spits out a list of each Zone Type in the Urban Model ID.
    '''
    query_        = True
    offset_       = 0
    use_type_list = []

    print(f"Starting to Query Urban Model ID: {urban_model_id}")
    print(" ")

    while query_:
        
        op = Operation(schema.Query)

        urban_database_count = op.urban_model(urban_model_id = urban_model_id)

        zone_types = urban_database_count.urban_database.zone_types(paging = {'limit': 100, 'offset': offset_})
        zone_types.attributes.global_id()
        zone_types.attributes.color()
        zone_types.attributes.label()
        zone_types.attributes.coverage_max()
        zone_types.attributes.dwelling_units_per_area_max()
        zone_types.attributes.farmax()
        zone_types.attributes.height_max()
        zone_types.attributes.net_area_factor()
        zone_types.attributes.num_floors_max()
        zone_types.attributes.zone_type_name()
        zone_types.attributes.allowed_space_use_types.space_use_type_id()
        zone_types.attributes.allowed_space_use_types.target_distribution()
        zone_types.attributes.skyplanes.adjacency()
        zone_types.attributes.skyplanes.angle()
        zone_types.attributes.skyplanes.horizontal_offset()
        zone_types.attributes.skyplanes.vertical_offset()
        zone_types.attributes.tiers.setbacks.front.interior.value()
        zone_types.attributes.tiers.setbacks.front.street.value()
        zone_types.attributes.tiers.setbacks.rear.interior.value()
        zone_types.attributes.tiers.setbacks.rear.street.value()
        zone_types.attributes.tiers.setbacks.side.interior.value()
        zone_types.attributes.tiers.setbacks.side.street.value()
        zone_types.attributes.tiers.start_height()
            
        print('Query set properly, continuining to querying of data...')

        offset_ += 100
        
        json_data = endpoint(op)
        errors = json_data.get('error')

        if errors:
            print(errors)
        else:
            print(f"Successfully queried data for offset {offset_ - 100} to {offset_}...")
            print(" ")

        data_out = endpoint(op)
        data_out = op + data_out
        
        len_data = len(data_out.urban_model.urban_database.zone_types)
        
        for i in range(len_data):
            use_type_list.append(data_out.urban_model.urban_database.zone_types[i])
        
        if len_data != 100:
            query_ = False 
        
    print("Done querying for all Zone Types...")

    return(use_type_list)

def parse_zone_type_table(use_type_list: List) -> List:
    '''
    Parses through the zone table and outputs a csv list to be used in a Pandas dataframe.
    '''

    print('Preparing to iterate through CSV list...')
    print(" ")

    csv_list = []

    for x in range(len(use_type_list)):

        print(f"Parsing through {use_type_list[x].attributes.label} Zone Type...")

        temp_hold_list = []

        temp_hold_list.append(use_type_list[x].attributes.global_id)
        temp_hold_list.append(use_type_list[x].attributes.color)
        temp_hold_list.append(use_type_list[x].attributes.label)
        temp_hold_list.append(use_type_list[x].attributes.coverage_max)
        temp_hold_list.append(use_type_list[x].attributes.dwelling_units_per_area_max)
        temp_hold_list.append(use_type_list[x].attributes.farmax)
        temp_hold_list.append(use_type_list[x].attributes.net_area_factor)
        temp_hold_list.append(use_type_list[x].attributes.num_floors_max)

        temp_hold_list.append(use_type_list[x].attributes.zone_type_name)
        if use_type_list[x].attributes.allowed_space_use_types == None or use_type_list[x].attributes.allowed_space_use_types == []:
            temp_hold_list.append('NO SPACE USE TYPE')
            temp_hold_list.append('NO SPACE USE TYPE')

        else:
            temp_hold_list.append(use_type_list[x].attributes.allowed_space_use_types[0].space_use_type_id)
            temp_hold_list.append(use_type_list[x].attributes.allowed_space_use_types[0].target_distribution)
            
        if use_type_list[x].attributes.skyplanes == None or use_type_list[x].attributes.skyplanes == []:
            temp_hold_list.append('NO SKYPLANES FOUND')
            temp_hold_list.append('NO SKYPLANES FOUND')
            temp_hold_list.append('NO SKYPLANES FOUND')
            temp_hold_list.append('NO SKYPLANES FOUND')

        else:

            temp_hold_list.append(use_type_list[x].attributes.skyplanes[0].adjacency)
            temp_hold_list.append(use_type_list[x].attributes.skyplanes[0].angle)
            temp_hold_list.append(use_type_list[x].attributes.skyplanes[0].horizontal_offset)
            temp_hold_list.append(use_type_list[x].attributes.skyplanes[0].vertical_offset)

        try:
            temp_hold_list.append(use_type_list[x].attributes.tiers[0].setbacks.front.interior.value)
        except:
            temp_hold_list.append("NO VALUE")
        try:
            temp_hold_list.append(use_type_list[x].attributes.tiers[0].setbacks.front.street.value)
        except:
            temp_hold_list.append("NO VALUE")
        try:
            temp_hold_list.append(use_type_list[x].attributes.tiers[0].setbacks.side.interior.value)
        except:
            temp_hold_list.append("NO VALUE")
        try:
            temp_hold_list.append(use_type_list[x].attributes.tiers[0].setbacks.side.street.value)
        except:
            temp_hold_list.append("NO VALUE")
        try:
            temp_hold_list.append(use_type_list[x].attributes.tiers[0].setbacks.rear.interior.value)
        except:
            temp_hold_list.append("NO VALUE")
        try:
            temp_hold_list.append(use_type_list[x].attributes.tiers[0].setbacks.rear.street.value)
        except:
            temp_hold_list.append("NO VALUE")
        try:
            temp_hold_list.append(use_type_list[x].attributes.tiers[0].start_height)
        except:
            temp_hold_list.append("NO VALUE")
        
        csv_list.append(temp_hold_list)

        print(f"Successfuly parced through {use_type_list[x].attributes.label} Zone Type...")
        print(" ")


    print(f"Successfuly created a list of {len(use_type_list)} Zone Types...")
    
    return csv_list

def zone_type_list_to_csv(csv_list: List, folder_path: str,  out_path_name: str ) -> None:
    '''
    Createss CSV list from pandas dataframe to be reviewed by customer...
    Headers for the dataframe are fixed...
    '''

    headers_ = ['GLOBAL_ID',
            'COLOR',
            'LABEL',
            'COVERAGE MAX',
            'DWELLING UNITS PER AREA MAX',
            'FAR MAX',
            'NET AREA FACTOR',
            'NUM FLOOR MAX',
            'ZONE_TYPE_NAME',
            'SPACE_USE_TYPE',
            'SPACE_USE_DISTR',
            'ADJANCY',
            'ANGLE',
            'HORIZON_OFF',
            'VERT_OFF',
            'FRONT_INT',
            'FRONT_STREET',
            'SIDE_INT',
            'SIDE_STREET',
            'BACK_INT',
            'BACK_STREET',
            'START_HEIGHT']
    
    df = pd.DataFrame(csv_list, columns = headers_)

    output_path = os.path.join(folder_path, out_path_name)

    if os.path.exists(output_path):
        os.remove(output_path)
        print(f"Deleted file: {output_path}")
        
    df.to_csv(output_path, index = False, encoding = 'utf-8')

    print("Done creating CSV for your review...")
   

def create_zone_types_from_csv(space_use_type_id: str,
                               global_id: str,
                               target_distribution: int,
                               front_int: int,
                               front_street: int,
                               rear_int:int,
                               rear_street:int,
                               side_int: int,
                               side_street: int,
                               start_height: int,
                               adjacency: int,
                               angle: int,
                               horizontal_offset: int,
                               vertical_offset: int,
                               orientation: str,
                               color_: str,
                               label_: str,
                               urban_model_database:str,
                               endpoint: HTTPEndpoint) -> None:
    
    '''
    Intakes a CSV and updates the Zone Types for given Urban Model ID
    '''

    front_ = "Front"

    allowed_space_use_types = {"spaceUseTypeID": global_id, 'targetDistribution': target_distribution}

    tiers = {'setbacks': {'front': {'interior': {'value': front_int}, 'street': {'value': front_street}}, 
                          'rear': {'interior': {'value':rear_int}, 'street': {'value':rear_street}}, 
                          'side': {'interior': {'value':side_int}, 'street': {'value':side_street}}}, 
            'startHeight': start_height}
    
    skyplanes = {'adjacency': 'Street', 
                 'angle': angle, 
                 'horizontalOffset': horizontal_offset, 
                 'verticalOffset': vertical_offset, 
                 'orientation': front_}
    
    attributes_dict = {'GlobalID': global_id, 
                    'AllowedSpaceUseTypes': [allowed_space_use_types], 
                    'Color': color_, 
                    'Label': label_,
                    'Skyplanes': [skyplanes],
                    'Tiers': [tiers]}
    
    zone_type_dict = {'attributes': attributes_dict}

    zone_type = [zone_type_dict]

    op = Operation(schema.Mutation)
    
    update_zone = op.update_zone_types(urban_database_id= urban_model_database,
                                      zone_types= zone_type)
    
    # print(update_zone)
    
    json_data_zones = endpoint(op)

    errors = json_data_zones.get('errors')

    if errors:
        print(errors)
    else:
        print(f"Successfully updated {label_} Zone Type...")

    print(" ")

    return None

