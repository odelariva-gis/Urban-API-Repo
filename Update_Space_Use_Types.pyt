### Import login information here...
### reloading the library to update the dictionary
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
import openpyxl as pxl
from openpyxl.utils.dataframe import dataframe_to_rows
import pandas as pd
import numpy as np

import utils_pro
import importlib
importlib.reload(utils_pro)

print("Finished importing libraries!")


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Update Space Use Type Metric Tools"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [GetZoneTypes, UpdateZoneTypes]


class GetZoneTypes(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Get Space Use Type Metrics"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Urban Model ID",
            name="urban_model_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        #param0.value = '87f1ea1760524426bd570a72b645133f'

        param1 = arcpy.Parameter(
            displayName="Output Folder Path",
            name="out_folder_path",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input")
        
        #param1.value = r'C:\Users\omar9125\OneDrive - Esri\Working_Files_7292022\UrbanAPI_Work_3212023\Metric_Output'
        

        param2 = arcpy.Parameter(
            displayName="Unit",
            name="unit_",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        param2.value = 'Standard'
        param2.filter.type = 'ValueList'
        param2.filter.list = ['Standard', 'Metric']


        # param3 = arcpy.Parameter(
        #     displayName="Configuration File",
        #     name="config_file",
        #     datatype="GPString",
        #     parameterType="Optional",
        #     direction="Input")



        params = [param0, param1, param2]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        # arcpy.env.outputZFlag = "Enabled"
        # arcpy.env.outputMFlag = "Same AS Input"
        # env.overwriteOutput = True
        # wksp_memo = 'in_memory'

        urban_model_id    = parameters[0].valueAsText
        folder_path       = parameters[1].valueAsText
        unit_type         = parameters[2].valueAsText
        #config_file       = parameters[3].valueAsText

        graph_url            = 'https://urban-api.arcgis.com/graphql'

        today = date.today()
        date_ = today.strftime("%Y%m%d") 

        utils_pro.get_message("Getting your Zone Type Metrics")

        ### log in information here
        source = utils_pro.loggin_agol('config.py')

        ### Reloading the utils_pro lib for config.py and print the authorization
        _auth = utils_pro.create_token_header('config.py', source)
        print(_auth)

        ### Create graph ql here
        endpoint = utils_pro.create_endpoint(graph_url, _auth)

        ### Query the data here from the GraphQL API...
        data_out = utils_pro.create_get_zone_metric_query(urban_model_id, 100, endpoint)

        ### Create dicts and lists here...
        id_dict, id_metric_dict, id_dict_list, id_metric_list = utils_pro.return_metric_dicts_lists(data_out)

        ### Create dictionary here for metric types...
        type_dict = utils_pro.get_metric_use_types(data_out)


        ### Query the space use metrics here...
        space_use_metric_list = utils_pro.query_space_use_type_metrics(data_out, id_dict, id_metric_dict, type_dict, unit_type) 

        ### Create excel sheet here from the metrics output..
        utils_pro.output_excel_metric_use_types(space_use_metric_list, date_, folder_path)

        return 
    
    def get_message(self, message):
        arcpy.AddMessage(message)

         
class UpdateZoneTypes(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Update Space Use Type Metrics"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        # param0 = arcpy.Parameter(
        #     displayName="Urban Model ID",
        #     name="urban_model_id",
        #     datatype="GPString",
        #     parameterType="Required",
        #     direction="Input")
        
        # param0.value = "87f1ea1760524426bd570a72b645133f"
        
        param0 = arcpy.Parameter(
            displayName="Urban Database ID",
            name="urban_database_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        #param0.value = "25e0ffee960948038abf83bab9f84968"

        param1 = arcpy.Parameter(
            displayName="Upload Excel",
            name="upload_excel",
            datatype="DEFile",
            parameterType="Required",
            direction="Input")
        
        #param1.value = r"C:\Users\omar9125\OneDrive - Esri\Working_Files_7292022\UrbanAPI_Work_3212023\Metric_Output\Urban_Use_Types_20240315_upload.xlsx"
        

        param2 = arcpy.Parameter(
            displayName="Unit",
            name="unit_",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        param2.value = 'Standard'
        param2.filter.type = 'ValueList'
        param2.filter.list = ['Standard', 'Metric']


        # param3 = arcpy.Parameter(
        #     displayName="Configuration File",
        #     name="config_file",
        #     datatype="GPString",
        #     parameterType="Optional",
        #     direction="Input")


        params = [param0, param1, param2]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        #urban_model_id     = parameters[0].valueAsText
        urban_database_id  = parameters[0].valueAsText
        upload_excel       = parameters[1].valueAsText
        unit_type          = parameters[2].valueAsText
        #config_file        = parameters[3].valueAsText

        ### GraphQL URL
        graph_url        = 'https://urban-api.arcgis.com/graphql'

        self.get_message("Getting your Zone Type Metrics")

        ### Get log in information here...
        source = utils_pro.loggin_agol('config.py')


        ### Reloading the utils_pro lib for config.py and print the authorization token here...
        ### You can use this authorization token in your Urban API sandbox if so desired, note to change the ' to " in the sandbox

        importlib.reload(utils_pro)
        _auth = utils_pro.create_token_header('config.py', source)
        print(_auth)

        ### Create GraphQL here....
        endpoint = utils_pro.create_endpoint(graph_url, _auth)

        ### Importing only one Excel sheet with one tab at a time...

        df_upload = pd.read_excel(upload_excel)
        df_upload = df_upload.replace(np.nan, None)
        pd_list = df_upload.values.tolist()

        ### Get the Metric ID list here from the pandas data frame...

        metric_frame_list = utils_pro.create_metric_source_id_list(pd_list, unit_type)

        ### Create query dictionary here...

        update_zone_dict = utils_pro.create_zone_type_metrics_dict(metric_frame_list)

        ###  Update the metrics here via the GraphQL here...

        utils_pro.update_zone_types_op(update_zone_dict, urban_database_id, endpoint, update_zone_dict)

        return

    def get_message(self, message):
        arcpy.AddMessage(message)