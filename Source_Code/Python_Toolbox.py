import arcpy
from arcpy import management
import math
import pathlib as ptlib
import tempfile
import statistics
from datetime import datetime
import numpy
import numpy as np
import pandas as pd
import rasterio
import scipy.constants
from rasterio import windows
from rasterio import plot
# OGR is used for Vector Data
from osgeo import ogr
# GDAL is used for Raster Data
from osgeo import gdal
from osgeo import gdalconst
import matplotlib.pyplot as plt
import time
import os
import shutil
import pandas
import glob
import re
import shapely.geometry
import random
from rasterio import mask, warp
import json
from scipy import constants

## ...---...###

arcpy.env.addOutputsToMap = True
class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Radiance_to_Kelvin, FRED_and_FRFD_Calculator, Ash_Temperature_Adjustor]

class Radiance_to_Kelvin:
    def __int__(self):
        self.label = "Radiance to Kelvin Converter"
        self.description = "Prior to calculating FRED, the user must convert their radiance values to Kelvin. Plancks function is used for conversions" + \
            "The user must know the central wavelength of the thermal infrared band they are using prior to running this function" + \
            "Output is a folder with a Kelvin raster stack that can be used for FRED/FRFD calculations"
    def getParameterInfo(self):
        """Define the tool parameters."""
        # To edit parameter descriptions, you must edit the associated XML file
        params = []
        # Central wavelength for Plancks Function
        Central_Wavelength = arcpy.Parameter(
            displayName="Central Wavelength",
            name="central_wavelength",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        # Input directory containing radiance mosaics
        Input_Raster_Directory = arcpy.Parameter(
            displayName="Input Rasters",
            name="input_rasters",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input")
        # Output location for Kelvin mosaics
        # When the function runs, the output directory will contain a new folder for kelvin mosaics
        Output_Directory = arcpy.Parameter(
            displayName="Output Location",
            name="output_location",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input")
        params.append(Output_Directory)
        params.append(Central_Wavelength)
        params.append(Input_Raster_Directory)
        return params
    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""

        def __List_Rasters(Path, file_type="tif"):
            path = ptlib.Path(Path)
            All_Rasters = list(path.glob('**/*.{}'.format(file_type)))
            Raster_List = []
            for raster in All_Rasters:
                Raster_Path = str(raster).replace("/", "\\")
                Raster_List.append(Raster_Path)
            return Raster_List
        parameters[1].clearMessage()
        list_of_rasters = __List_Rasters(parameters[1].ValueAsText)
        if len(list_of_rasters) == 0:
            parameters[1].setErrorMessage("There is not a raster in the folder pathway")
        else:
            parameters[1].message("Folder pathway contains {} rasters".format(len(list_of_rasters)))
        return
    # All functions will be run in this method
    # Convert radiance to Kelvin
    def execute(self, parameters, messages):
        """The source code of the tool."""
        # This is where the conversion code goes
        # Establish temporary directory to store individual kelvin mosaics
        temporary_directory = tempfile.mkdtemp()
        # Initialize parameters as text for functions
        input_raster_location = parameters[1].ValueAsText
        central_wavelength = parameters[0].ValueAsText
        output_location = parameters[2].ValueAsText
        def Plancks_Function(Array, w):
            """
            Plancks function that converts radiances to Kelvin

            :param Array:
            :return:
            """
            # Outputs Kelvin
            L = Array.astype(float) / 100
            c1 = 1.1910E8
            c2 = 1.439E4
            T = (c2) / (w * (np.log((c1 / ((w ** 5) * L)) + 1)))
            T[(T == float("inf"))] = 0
            print(T.max())
            return T

        def __List_Rasters(Path, file_type="tif"):
            path = ptlib.Path(Path)
            All_Rasters = list(path.glob('**/*.{}'.format(file_type)))
            Raster_List = []
            for raster in All_Rasters:
                Raster_Path = str(raster).replace("/", "\\")
                Raster_List.append(Raster_Path)
            return Raster_List

        def Temperature_Rasters(raster_path, output_location, w):
            rasters = __List_Rasters(raster_path)
            if len(rasters) > 1:
                for i in range(0, len(rasters)):
                    file_name = os.path.basename(rasters[i])
                    # Grab the pass number from the file name
                    image_n = file_name[0:5]
                    raster = rasterio.open(rasters[i])
                    out_meta = raster.meta
                    array = raster.read(1)
                    Temp_array = Plancks_Function(
                        Array=array,
                        w=w)
                    out_meta.update({'dtype': "float32"})
                    with rasterio.open("{}/{}_Float.tif".format(output_location, image_n), 'w', **out_meta) as dst:
                        dst.nodata = None
                        dst.write(Temp_array, 1)
            else:
                file_name = os.path.basename(rasters[0])
                # Grab the pass number from the file name
                image_n = file_name[0:2]
                raster = rasterio.open(rasters[0])
                out_meta = raster.meta
                array = raster.read(1)
                Temp_array = Plancks_Function(
                    Array=array,
                    w=w)
                out_meta.update({'dtype': "float32"})
                with rasterio.open("{}/{}_Float.tif".format(output_location, image_n), 'w', **out_meta) as dst:
                    dst.nodata = None
                    dst.write(Temp_array, 1)

        def Raster_Stack(output_location, raster_path):
            temp = tempfile.mkdtemp()
            try:
                # Open each raster in the list of rasters
                rasters = __List_Rasters(raster_path)
                # Compare the extents of the first two rasters and create a new raster with their overlapping bounding box
                intersection = None
                with rasterio.open(rasters[0]) as r_1, rasterio.open(rasters[1]) as r_2:
                    ext1 = shapely.geometry.box(*r_1.bounds)
                    ext2 = shapely.geometry.box(*r_2.bounds)
                    # Determine intersection for first two rasters
                    intersection = ext1.intersection(ext2)
                for i in range(2, len(rasters)):
                    # Determine intersection for each raster until the extent at which all rasters intersect will be identified and used for
                    r = rasterio.open(rasters[i])
                    ext_1 = shapely.geometry.box(*intersection.bounds)
                    ext_2 = shapely.geometry.box(*r.bounds)
                    # Update the intersection variable over time
                    intersection = ext_1.intersection(ext_2)
                # Use the intersection to clip the first raster. Use the metadata and transform from that clipped raster as the
                # Base raster is the clipped raster with the new extent and transformed with the transform from the mask output
                geom = shapely.geometry.mapping(intersection)
                n = 0
                out_meta = None
                location_list = []
                for r in rasters:
                    n += 1
                    src = rasterio.open(r)
                    ra = src.read(1)
                    out_meta = src.meta
                    clip_image, clip_transform = rasterio.mask.mask(src, [geom], crop=True)
                    out_meta.update({"height": clip_image.shape[1],
                                     "width": clip_image.shape[2],
                                     "transform": clip_transform})
                    with rasterio.open("{}/C_{}.tif".format(temp, n), "w", **out_meta) as new:
                        new.write(clip_image)
                    location_list.append("{}/C_{}.tif".format(temp, n))
                    src = None
                out_meta.update({'count': len(rasters)})
                n = 0
                with rasterio.open("{}/Kelvin_Stack.tif".format(output_location), 'w', **out_meta) as src_1:
                    for l in location_list:
                        n += 1
                        src_2 = rasterio.open(l)
                        src_1.write(src_2.read(1), n)
            except Exception as e:
                temp = None
                raster = None
                print(e)
        arcpy.AddMessage("Converting Radiances to Kelvins")
        Temperature_Rasters(
            raster_path=input_raster_location,
            output_location=temporary_directory,
            w=central_wavelength)
        arcpy.AddMessage("Stacking rasters to create Kelvin raster stack")
        Raster_Stack(
            output_location=output_location,
            raster_path=temporary_directory)
        shutil.rmtree(temporary_directory)
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
#
"""
Add multiple booleans:
    - Peak FRFD? 
    - Output Statistics?
    - Automated Map?
    
Start with Peak FRFD and output statistics and move on from there

FRED_FRFD_Statistics = arcpy.Parameter(displayName="FRED & FRFD Statistics",
                                           name="output_location",
                                           datatype="GPBoolean",
                                           parameterType="Optional",
                                           direction="Input")
Peak_FRFD = arcpy.Parameter(displayName="FRED & FRFD Statistics",
                                           name="output_location",
                                           datatype="GPBoolean",
                                           parameterType="Optional",
                                           direction="Input")

"""

class FRED_and_FRFD_Calculator:
    def __init__(self):
        self.label = "FRED and FRFD Calculator"
        self.description = ""
    def getParameterInfo(self):
        """Define the tool parameters."""
        # To edit parameter descriptions, you must edit the associated XML file
        params = []
        # Input_Raster_Directory
        Input_Raster_Directory = arcpy.Parameter(
            displayName="Input Rasters",
            name="input_raster",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Input")
        Ambient_Temperature = arcpy.Parameter(displayName="Ambient Temperature",
            name="ambient_temp",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        Pass_Time_Table = arcpy.Parameter(displayName = "Pass Time Table",
                                           name = "pass_time_table",
                                           datatype = "DETable",
                                           parameterType="Required",
                                           direction = "Input")
        Image_Pass_Times = arcpy.Parameter(displayName = "Image Pass Time Field",
                                           name = "image_pass_times",
                                           datatype = "GPString",
                                           parameterType="Required",
                                           direction = "Input",
                                           multiValue = True)
        Output_Directory = arcpy.Parameter(displayName="Output Location",
                                           name="output_location",
                                           datatype="DEFolder",
                                           parameterType="Required",
                                           direction="Input")
        Image_Pass_Times.enabled = False
        Ambient_Temperature.value = 289
        params = [Input_Raster_Directory, Ambient_Temperature, Pass_Time_Table, Image_Pass_Times, Output_Directory]
        return params
    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[2].altered == True:
            parameters[3].enabled = True
            times = parameters[2].ValueAsText
            flds = [f.name for f in arcpy.ListFields(times)]
            parameters[3].filter.list = flds
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""
        return
    def execute(self, parameters, messages):
        """The source code of the tool."""
        # This is where the conversion code goes
        # Create scratch folder for separated FRFDs
        # Use os.path.join with this location when calculating FRFD
        frfd_temp = arcpy.env.scratchFolder
        # Load the parameters as text
        input_raster = parameters[0].ValueAsText
        ambient_temperature = parameters[1].ValueAsText
        pass_time_table = parameters[2].ValueAsText
        image_pass_time = parameters[3].ValueAsText
        out_put_path = parameters[4].ValueAsText
        arcpy.AddMessage(out_put_path)
        FRED_output_location = os.path.join(out_put_path + '\FRED')
        if os.path.exists(FRED_output_location):
            filelist = os.listdir(FRED_output_location)
            if len(filelist) >= 0:
                for f in filelist:
                    os.remove(os.path.join(FRED_output_location, f))
            os.rmdir(FRED_output_location)
            os.mkdir(FRED_output_location)
        else:
            os.mkdir(FRED_output_location)
        FRFD_output_location = os.path.join(out_put_path + '\FRFD_Stack')
        if os.path.exists(FRFD_output_location):
            filelist = os.listdir(FRFD_output_location)
            if len(filelist) >= 0:
                for f in filelist:
                    os.remove(os.path.join(FRFD_output_location, f))
            os.rmdir(FRFD_output_location)
            os.mkdir(FRFD_output_location)
        else:
            os.mkdir(FRFD_output_location)
        FRFDs_output_location = os.path.join(out_put_path + '\FRFD_Rasters')
        if os.path.exists(FRFDs_output_location):
            filelist = os.listdir(FRFDs_output_location)
            arcpy.AddMessage(filelist)
            if len(filelist) >= 0:
                for f in filelist:
                    os.remove(os.path.join(FRFDs_output_location, f))
            os.rmdir(FRFDs_output_location)
            os.mkdir(FRFDs_output_location)
        else:
            os.mkdir(FRFDs_output_location)
        # Load the raster as an arcpy raster object
        kelvin_raster = arcpy.sa.Raster(input_raster)
        # Get the band count from the Kelvin Raster and create a loop to extract the band
        bands = kelvin_raster.bandCount
        # Create list of Raster objects that will be used for calculations
        kelvin_rasters = []
        for b in range(1, bands+1):
            # Extract an individual band from the raster
            single_raster = arcpy.ia.ExtractBand(kelvin_raster, [b])
            kelvin_rasters.append(single_raster)
        # With the list of raster objects, calculate FRFD
        # I guess just use arithmetic and append to list?
        FRFD_Rasters = []
        s = scipy.constants.sigma
        FRFD_Raster_Locations = []
        # Consider creating output statistics for FRED and FRFD Rasters
        for i in range(0, len(kelvin_rasters)):
            r = arcpy.Raster(kelvin_rasters[i])
            at = int(ambient_temperature)
            frfd_raster = s*(r**4 - at**4)
            FRFD_Rasters.append(frfd_raster)
            # Output Raster Location
            FRFD_Raster_Locations.append("{}/{}".format(FRFDs_output_location, 'FRFD_{}.tif'.format(i+1)))
            arcpy.AddMessage("{}".format(arcpy.Raster(FRFD_Rasters[i]).maximum))
            frfd_raster.save("{}/{}".format(FRFDs_output_location, 'FRFD_{}.tif'.format(i+1)))
            del frfd_raster
        del kelvin_rasters
        # After calculating FRFD, get the pass times for FRED calculations
        pass_times = []
        # Create a Search Cursor to retrieve values from a specific attribute in the table
        with arcpy.da.SearchCursor(pass_time_table, [image_pass_time]) as cursor:
            for row in cursor:
                pass_times.append(row[0])
        # Adapt FRED function based on raster calculator
        # First, create a loop that includes the two rasters, as well as the pass times converted into time past (seconds).
        FREDs = []
        arcpy.AddMessage(len(FRFD_Rasters))
        arcpy.AddMessage(len(pass_times))
        arcpy.AddMessage(pass_times)
        for d in range(1, len(FRFD_Rasters)):
            # Collect the current date. To do subtractions between times you need a date
            date = datetime.now().date()
            # First time
            t1 = datetime.combine(date, pass_times[d-1])
            # Second time
            t2 = datetime.combine(date, pass_times[d])
            arcpy.AddMessage("{}".format(d))
            #Time change
            delta = t2-t1
            # Calculate the sum of two FRFD Rasters
            FRFD_Sum = (FRFD_Rasters[d] + FRFD_Rasters[d-1])
            # Calculate FRED
            FRED = ((FRFD_Sum) * delta.seconds) * 0.5
            del FRFD_Sum
            FREDs.append(FRED)
            del FRED
        # Establish a base raster for calculations
        total_fred = FREDs[0]
        # Calculate the FRED by summing all FRED calculations (trapezoids)
        for f in FREDs[1:]:
            total_fred = arcpy.sa.Plus(f, total_fred)
        arcpy.AddMessage("FRED has been calculated")
        del FREDs
        # Save the output FRED raster to the identified location
        total_fred.save(os.path.join(FRED_output_location, "FRED_{}".format(ambient_temperature)))
        arcpy.AddMessage("FRED has been exported")
        del total_fred
        # Create output string for composite band raster function
        frfd_rasters = ";".join(FRFDs_output_location)
        arcpy.CompositeBands_management(in_rasters=frfd_rasters, out_raster=FRFD_output_location)
        arcpy.AddMessage("FRFD stack has been exported")
        del frfd_rasters

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""

class Ash_Temperature_Adjustor:
    def __init__(self):
        self.label = "FRED and FRFD Calculator"
        self.description = ""
    def getParameterInfo(self):
        """Define the tool parameters."""
        # To edit parameter descriptions, you must edit the associated XML file
        params = []
        # Input_Raster_Directory
        Input_Raster_Directory = arcpy.Parameter(
            displayName="Input Kelvin Raster",
            name="input_raster",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Input")
        Ambient_Temperature = arcpy.Parameter(displayName="Ambient Temperature",
            name="ambient_temp",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        Ash_Temperature = arcpy.Parameter(displayName="Ambient Temperature",
            name="ash_temp",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        Pass_Time_Table = arcpy.Parameter(displayName = "Pass Time Table",
                                           name = "pass_time_table",
                                           datatype = "DETable",
                                           parameterType="Required",
                                           direction = "Input")
        Image_Pass_Times = arcpy.Parameter(displayName = "Image Pass Time Field",
                                           name = "image_pass_times",
                                           datatype = "GPString",
                                           parameterType="Required",
                                           direction = "Input",
                                           multiValue = True)
        Output_Directory = arcpy.Parameter(displayName="Output Location",
                                           name="output_location",
                                           datatype="DEFolder",
                                           parameterType="Required",
                                           direction="Input")
        Image_Pass_Times.enabled = False
        Ambient_Temperature.value = 289
        params.append(Input_Raster_Directory)
        params.append(Ambient_Temperature)
        params.append(Pass_Time_Table)
        params.append(Image_Pass_Times)
        params.append(Output_Directory)
        params.append(Ash_Temperature)
        return params
    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[2].altered == True:
            parameters[3].enabled = True
            times = parameters[2].ValueAsText
            flds = [f.name for f in arcpy.ListFields(times)]
            parameters[3].filter.list = flds
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""
        return
    def execute(self, parameters, messages):
        """The source code of the tool."""
        # This is where the conversion code goes
        # Create scratch folder for separated FRFDs
        # Use os.path.join with this location when calculating FRFD
        def Get_Raster_Info(raster):
            "Extract raster information through GDAL"
            r = gdal.Open(raster)
            cols = r.RasterXSize
            rows = r.RasterYSize
            bands = r.RasterCount
            geotransform = r.GetGeoTransform()
            projection = r.GetProjection()
            metadata = r.GetMetadata()
            raster_info = {
                'cols': cols,
                'rows': rows,
                'bands': bands,
                'projection': projection,
                'metadata': metadata
            }
            return raster_info
        def Create_Output_Raster(raster_info, array):
            "Output raster through GDAL"
            pass
        frfd_temp = arcpy.env.scratchFolder
        # Load the parameters as text
        input_raster = parameters[0].ValueAsText
        ambient_temperature = parameters[1].ValueAsText
        pass_time_table = parameters[2].ValueAsText
        image_pass_time = parameters[3].ValueAsText
        out_put_path = parameters[4].ValueAsText
        arcpy.AddMessage(out_put_path)
        FRED_output_location = os.path.join(out_put_path + '\Ash_FRED')
        if os.path.exists(FRED_output_location):
            filelist = os.listdir(FRED_output_location)
            if len(filelist) >= 0:
                for f in filelist:
                    os.remove(os.path.join(FRED_output_location, f))
            os.rmdir(FRED_output_location)
            os.mkdir(FRED_output_location)
        else:
            os.mkdir(FRED_output_location)
        FRFD_output_location = os.path.join(out_put_path + '\Ash_FRFD_Stack')
        if os.path.exists(FRFD_output_location):
            filelist = os.listdir(FRFD_output_location)
            if len(filelist) >= 0:
                for f in filelist:
                    os.remove(os.path.join(FRFD_output_location, f))
            os.rmdir(FRFD_output_location)
            os.mkdir(FRFD_output_location)
        else:
            os.mkdir(FRFD_output_location)
        FRFDs_output_location = os.path.join(out_put_path + '\Ash_FRFD_Rasters')
        if os.path.exists(FRFDs_output_location):
            filelist = os.listdir(FRFDs_output_location)
            arcpy.AddMessage(filelist)
            if len(filelist) >= 0:
                for f in filelist:
                    os.remove(os.path.join(FRFDs_output_location, f))
            os.rmdir(FRFDs_output_location)
            os.mkdir(FRFDs_output_location)
        else:
            os.mkdir(FRFDs_output_location)
        # Load the raster as an arcpy raster object
        # Load up gdal object and extract specific information from the gdal object
        # This is to easily convert the numpy arrays extracted into output rasters
        # Get the band count from the Kelvin Raster and create a loop to extract the band
        # Create list of numpy arrays that will be used for calculations
        raster_info = Get_Raster_Info(input_raster)
        Kelvin_raster = gdal.Open(input_raster)
        kelvin_rasters = []
        for b in range(1, raster_info["bands"]+1):
            # Extract an individual band from the raster
            single_raster = Kelvin_raster.GetRasterBand(b)
            # Convert the raster into a numpy array
            k_raster = single_raster.ReadAsArray(0,0,raster_info["cols"],raster_info["rows"])
            # Append the numpy array to the list of kelvin rasters
            kelvin_rasters.append(k_raster)
        # Conver the list of rasters into a numpy dstack
        kelvin_stack = np.dstack(kelvin_rasters)
        # Extract extent of the rasters
        rows = kelvin_rasters[1].shape[0]
        cols = kelvin_rasters[1].shape[1]
        # Create an empty array based on the extent of the raster
        fred_array = np.zeros_like(kelvin_rasters[1])
        FRFD_Rasters = []
        s = scipy.constants.sigma
        FRFD_Raster_Locations = []
        pass_times = []
        # Create a Search Cursor to retrieve values from a specific attribute in the table
        with arcpy.da.SearchCursor(pass_time_table, [image_pass_time]) as cursor:
            for row in cursor:
                pass_times.append(row[0])
        for i in range(0, rows):
            for j in range(0, cols):
                # Determine if the pixel was imaged burning
                Temp_profile = kelvin_stack[i][j]
                if max(kelvin_stack)[i][j] <473:
                    FRFD_list = []
                    FRED_list = []
                    # Calculate FRED normally
                    for t in Temp_profile:
                        FRFD_AT = s * (int(ambient_temperature) ** 4)
                        FRFD_T = s * (t ** 4)
                        FRFD = FRFD_T - FRFD_AT
                        if FRFD < 0:
                            FRFD_list.append(0)
                        else:
                            FRFD_list.append(FRFD)
                    for b in range(1, len(FRFD_list)):
                        FRFD_2 = FRFD_list[b]
                        # Call the first FRFD array
                        FRFD_1 = FRFD_list[b - 1]
                        # Call the first Time in the list
                        Time_1 = pass_times[b - 1]
                        # Call the second Time in the list
                        Time_2 = pass_times[b]
                        # Convert the times to date time classes
                        t1 = datetime.strptime(Time_1, "%H:%M:%S")
                        # Conver the times to date teime classes
                        t2 = datetime.strptime(Time_2, "%H:%M:%S")
                        # Get the difference between the two time classes
                        delta = t2 - t1
                        # Sum up the FRFD calculations
                        FRFD_Sum = (FRFD_2 + FRFD_1)
                        # Any values less than 0 are converted to 0 (pixels that have temperatures below ambient
                        if FRFD_Sum <= 0:
                            FRFD_Sum = 0
                        # Calculate the FRED and add it to the FRED list
                        FRED = ((FRFD_Sum) * delta.seconds) * 0.5
                        FRED_list.append(FRED)
                    fred_array[i][j] = sum(FRED_list)
                    for ind, p in enumerate(FRFD_list):
                        kelvin_stack[ind][i][j] = p
                else:
                    FRFD_list = []
                    FRED_list = []
                    # Calculate FRED normally
                    FRFDs = {"Pre": [],
                             "Post": []}
                    for t in Temp_profile:
                        FRFD_AT = s * (int(ambient_temperature) ** 4)
                        FRFD_T = s * (t ** 4)
                        FRFD = FRFD_T - FRFD_AT
                        if FRFD < 0:
                            FRFD_list.append(0)
                        else:
                            FRFD_list.append(FRFD)
                    for b in range(1, len(FRFD_list)):
                        FRFD_2 = FRFD_list[b]
                        # Call the first FRFD array
                        FRFD_1 = FRFD_list[b - 1]
                        # Call the first Time in the list
                        Time_1 = pass_times[b - 1]
                        # Call the second Time in the list
                        Time_2 = pass_times[b]
                        # Convert the times to date time classes
                        t1 = datetime.strptime(Time_1, "%H:%M:%S")
                        # Conver the times to date teime classes
                        t2 = datetime.strptime(Time_2, "%H:%M:%S")
                        # Get the difference between the two time classes
                        delta = t2 - t1
                        # Sum up the FRFD calculations
                        FRFD_Sum = (FRFD_2 + FRFD_1)
                        # Any values less than 0 are converted to 0 (pixels that have temperatures below ambient
                        if FRFD_Sum <= 0:
                            FRFD_Sum = 0
                        # Calculate the FRED and add it to the FRED list
                        FRED = ((FRFD_Sum) * delta.seconds) * 0.5
                        FRED_list.append(FRED)
                    fred_array[i][j] = sum(FRED_list)
                    for ind, p in enumerate(FRFD_list):
                        kelvin_stack[ind][i][j] = p
        del kelvin_rasters
        # After calculating FRFD, get the pass times for FRED calculations
        # Adapt FRED function based on raster calculator
        # First, create a loop that includes the two rasters, as well as the pass times converted into time past (seconds).
        FREDs = []
        arcpy.AddMessage(len(FRFD_Rasters))
        arcpy.AddMessage(len(pass_times))
        arcpy.AddMessage(pass_times)
        for d in range(1, len(FRFD_Rasters)):
            # Collect the current date. To do subtractions between times you need a date
            date = datetime.now().date()
            # First time
            t1 = datetime.combine(date, pass_times[d-1])
            # Second time
            t2 = datetime.combine(date, pass_times[d])
            arcpy.AddMessage("{}".format(d))
            #Time change
            delta = t2-t1
            # Calculate the sum of two FRFD Rasters
            FRFD_Sum = (FRFD_Rasters[d] + FRFD_Rasters[d-1])
            # Calculate FRED
            FRED = ((FRFD_Sum) * delta.seconds) * 0.5
            del FRFD_Sum
            FREDs.append(FRED)
            del FRED
        # Establish a base raster for calculations
        total_fred = FREDs[0]
        # Calculate the FRED by summing all FRED calculations (trapezoids)
        for f in FREDs[1:]:
            total_fred = arcpy.sa.Plus(f, total_fred)
        arcpy.AddMessage("FRED has been calculated")
        del FREDs
        # Save the output FRED raster to the identified location
        total_fred.save(os.path.join(FRED_output_location, "FRED_{}".format(ambient_temperature)))
        arcpy.AddMessage("FRED has been exported")
        del total_fred
        # Create output string for composite band raster function
        frfd_rasters = ";".join(FRFDs_output_location)
        arcpy.CompositeBands_management(in_rasters=frfd_rasters, out_raster=FRFD_output_location)
        arcpy.AddMessage("FRFD stack has been exported")
        del frfd_rasters

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""



class Binary_Classifiers:
    def __init__(self):
        self.label = "Binary Classifer"
        self.description = "Classifies individual pixels based on their temporal characteristics. Includes 3 classifcations: Burned, Completed, Obscured"






