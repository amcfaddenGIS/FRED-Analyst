import arcpy
from arcpy import mp
from arcpy import sa
from arcpy import ia
from arcpy import analysis
import os
from scipy import constants
from PIL import Image

"""
Work on this tomorrow (fuck sake)
Logic:
    - Find map project (current project) 
    - Create a new map 
    - Create a new layout (with specified layout extent)
    - Create a map frame with specific coordinates 
    - Add elements (up to the user)
    - Add dynamic title that changes based on the flight pass time and the image number 
    
    
ALL DATA IS ADDED USING THE createMapSurroundElement Method for layouts
Data: 
    - FRFD Stack:
        - Each band in the image stack will be visualized and added to the layout 
        - The layout will be exported to a temporary folder as a PNG
        - The PNGs will be stacked to create a gif 
    - Times:
        - Image times provided by the user in csv format 
    - Output Location:
        - Folder location for the animation
    - Prefered Extent 
        - IF you have a specific area that you want to animate, you can provide a shapefile  
"""
# Initialize the toolbox to contain the varying tools.
class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [FRFD_Animator]


class FRFD_Animator:
    def __int__(self):
        self.label = "FRFD Animation"
        self.description = "Create an animation showing the progression of measured FRFDs for each image pass"
    def getParameterInfo(self):
        """Define the tool parameters."""
        # To edit parameter descriptions, you must edit the associated XML file
        Output_Directory = arcpy.Parameter(displayName="Output Location",
                                            name="output_location",
                                            datatype="DEFolder",
                                            parameterType="Required",
                                            direction="Input")
        Pass_Time_Table = arcpy.Parameter(displayName="Pass Time Table",
                                          name="pass_time_table",
                                          datatype="DETable",
                                          parameterType="Required",
                                          direction="Input")
        Image_Pass_Times = arcpy.Parameter(displayName="Image Pass Time Field",
                                           name="image_pass_times",
                                           datatype="GPString",
                                           parameterType="Required",
                                           direction="Input",
                                           multiValue=True)
        Input_FRFD_Raster = arcpy.Parameter(displayName="Input FRFD Raster",
                                            name="frfd_raster",
                                            datatype="DERasterDataset",
                                            parameterType="Required",
                                            direction="Input")
        params = [Input_FRFD_Raster, Pass_Time_Table, Image_Pass_Times, Output_Directory]
    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[1].altered == True:
            parameters[2].enabled = True
            times = parameters[1].ValueAsText
            flds = [f.name for f in arcpy.ListFields(times)]
            parameters[2].filter.list = flds
        return
    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""
        return
    def execute(self, parameters, messages):
        """The source code of the tool."""
        def MakeRec_LL(llx, lly, w, h):
            # Provide specifications for placing elements in image
            xyRecList = [[llx, lly], [llx, lly + h], [llx + w, lly + h], [llx + w, lly], [llx, lly]]
            array = arcpy.Array([arcpy.Point(*coords) for coords in xyRecList])
            rec = arcpy.Polygon(array)
            return rec
        def Create_Raster_Buffer(raster, output_location, map, map_frame):
            """
            Function creates buffer around raster for identifying the extent of a mapframe.
            Sets the map frame of the map frame based on the size of the buffer

            :param raster: Input raster
            :param output_location: Output location for the raster buffer
            :param map: Map that the layer will be added to
            :param map_frame: Map frame that will have its extent set
            :return: Raster buffer location
            """
            desc = arcpy.Describe(raster)
            extent = raster.extent
            cell_size = desc.children[0].meanCellHeight
            # Create constant rater with 0 values
            constant_raster = sa.CreateConstantRaster(constant_value=0,
                                                      data_type='INTEGER',
                                                      cell_size=cell_size,
                                                      extent=extent)
            raster_polygon_location = os.path.join(output_location,
                                                   'raster_polygon.shp')
            buffer_polygon_location = os.path.join(output_location,
                                                   'raster_buffer.shp')
            # Conver the raster to a polygon so a buffer can be drawn around it
            arcpy.RasterToPolygon_conversion(in_raster=constant_raster,
                                             out_polygon_features=raster_polygon_location,
                                             simplify="SIMPLIFY",
                                             raster_field="VALUE")
            # Create the buffer around the raster to polygon
            analysis.Buffer(in_features=raster_polygon_location,
                            out_feature_class=buffer_polygon_location,
                            buffer_distance_or_field='500 Meters')
            map.addDataFromPath(buffer_polygon_location)
            buf = map.listLayers()[0]
            layer_extent = map_frame.getLayerExtent(buf)
            map_frame.panToExtent(layer_extent)
            m.removeLayer(buf)
        def Create_Output_Images(raster, text_element, times, raster_temp, output_location):
            """
            Create output images of the layouts containing various rasters and times

            :param raster:
            :param raster_temp:
            :param output_location:
            :return:
            """
            bands = raster.bandCount
            reclass_location = os.path.join(raster_temp, 'reclass_raster')
            os.mkdir(reclass_location)
            # Create ambient temperature FRFD for remapping purposes
            s = constants.sigma
            ambient_FRFD = s * (289 ** 4)
            image_locations = []
            for b in range(1, bands + 1):
                # Create output location for the layout
                output = fr'{output_location}/layout_{b}.png'
                image_locations.append(output)
                # Extract an individual band from the raster
                single_raster = ia.ExtractBand(raster, [b])
                # To properly reclassify the raster, it must be converted into an integer raster
                int_raster = sa.Int(single_raster)
                # Calculate Maximum FRFD
                max_frfd = int_raster.maximum
                del single_raster
                # After the raster is converted into an int raster, create a reclassify range for reclasses the raster
                Reclass_range = sa.RemapRange([[0, ambient_FRFD, 'NoData'], [ambient_FRFD, int_raster.maximum, 1]])
                reclass_raster = sa.Reclassify(int_raster, 'Value', Reclass_range)
                out_rc_multi_raster = sa.RasterCalculator([reclass_raster, int_raster],
                                                          ["x", "y"], "x*y")
                del int_raster
                del reclass_raster
                # Save the reclassified raster and add it to the map
                out_rc_multi_raster.save(os.path.join(reclass_location, f'reclass_{b}.tif'))
                del out_rc_multi_raster
                m.addDataFromPath(os.path.join(reclass_location, f'reclass_{b}.tif'))
                # Next, replace the title text with the time the imagery was collected
                text_element.text = text_element.text.replace(text_element.text,
                                                times[b-1] + f" <FNT style='Bold'>Max FRFD</FNT>: {max_frfd} kW")
                # Output the frame
                lyt.exportToPNG(output)
                # Remove the raster from the map delete it
                m.removeLayer(m.listLayers()[0])
                filelist = os.listdir(reclass_location)
                for f in filelist:
                    os.remove(os.path.join(reclass_location, f))
                del filelist
                return image_locations
        # Import all parameters
        input_raster = parameters[0].ValueAsText
        pass_time_table = parameters[1].ValueAsText
        pass_time_field = parameters[2].ValueAsText
        output_location = parameters[3].ValueAsText
        # Identify the location of the ArcGIS Project
        proj = mp.ArcGISProject('current')
        # Identify file location for project
        project_location = os.path.split(proj.filePath)[0]
        # Create folder for the output rasters and shapefiles
        raster_temp = os.path.join(project_location, 'output_rasters')
        os.mkdir(raster_temp)
        # Create folder foer the output images/layouts
        image_temp = os.path.join(project_location, 'output_images')
        os.mkdir(image_temp)
        frfd_raster = sa.Raster(input_raster)
        # Create base layout that will be extracted as an image numerous times
        lyt = proj.createLayout(4.5, 3, 'INCH', 'Base_Layout')
        # Create new map
        m = proj.createMap('FRFD_Map')
        # Create a Map Frame within the extent of the project layout
        mf = lyt.createMapFrame(MakeRec_LL(0, 0.4, 4.5, 2.25), m, "FRFD_Map_Frame")
        time_list = []
        # Use search cursor to remove the values from the rows
        with arcpy.da.SearchCursor(pass_time_table, [pass_time_field]) as cursor:
            for row in cursor:
                time_list.append(row[0])
        dynamic_text = []
        for r in time_list:
            replace = f"<FNT style='Bold'>Time</FNT>: {r}"
            dynamic_text.append(replace)
        # Add dynamic title to the top of the map frame
        txtStyleItem = proj.listStyleItems('ArcGIS 2D', 'TEXT', 'Title (Sans Serif)')[0]
        ptTxt = proj.createTextElement(lyt, arcpy.Point(2.25, 2.8), 'POINT',
                                       '', 16, style_item=txtStyleItem)
        # Edit the center point of the text box
        ptTxt.setAnchor('Center_Point')
        # Change the font family for the text
        ptTxt.fontFamilyName = 'Avenir Next LT Pro'
        # Establish the X and y positions for the text
        ptTxt.elementPositionX = 2.25
        ptTxt.elementPositionY = 2.8
        # All the stuff below can be added to a independent function that is created in the python module
        # Establish the extent of the layout map frame by using the Create Raster Buffer function
        Create_Raster_Buffer(raster=frfd_raster,
                             output_location=raster_temp,
                             map=m,
                             map_frame=mf)
        # Loop through each of the rasters and export the band as a new raster using the Create output images function
        image_locations = Create_Output_Images(raster=frfd_raster,
                             times=dynamic_text,
                             text_element=ptTxt,
                             output_location=output_location,
                             raster_temp=raster_temp)
        # With the image locations, create a gif
        images = [Image.open(i) for i in image_locations]
        frame_1 = images[0]
        frame_1.save("{}/FRFD_Progression.gif".format(output_location), format="GIF",
                         append_images=images,
                         save_all=True, duration=150)
        def postExecute(self, parameters):
            """This method takes place after outputs are processed and
            added to the display."""





