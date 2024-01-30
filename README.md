# FRED-Analyst
**FRED Analyst:** An ArcGIS Python toolbox for estimating fire intensity through thermal infrared radiation imagery. 

<div align="center">
  <img src="https://github.com/amcfaddenGIS/FRED-Analyst/blob/main/Images/Spatial_Distribution.png" alt="Image with Text" />
</div>
<p align="center">Fire Radiative Energy Density estimations from the Thomas Fire</p>

## **Background**


### *What is Fire Intensity?*

As fuels are actively combusted during a wildfire, a significant amount of energy is release/produced. The quantification of this energy release is known as fire intensity, and it is measured in a variety of ways. THe most commonly referenced estimation of fire intensity is fireline intensity, which is the rate of energy released per unit time per unit length of the fire front (W/m). Rothermel's reaction intensity is the heat source for the Rothermel fire propagation model, measured in W/m^2. 

### *Measuring Fire Intensity Through Remote Sensing*
The  determination of fireline intensity for active wildfires is often difficult, due to a lack of necessary data, including the challenge of measuring fuel load prior to combustion and calculating fire rate of spread. However, through the use of short wave infrared and thermal infrared radiation, wildfire researchers can estimate fire intensity (specifically Rothermel Intensity). This includes the application of satellite platforms (MODIS, Landsat, Sentinel, etc.), and aerial platforms (FireMapper, FIRIS, etc.). 

A common method for approximating fire intensity is calculating the Fire Radiative Flux Density (FRFD), measured in W/m^2. To calculate FRFD, one must assume the fire is a black body radiator emitting TIR radiance. With this assumption, black-body equivalent temperature calculated from upwelling radiance and the Stefan Boltzmann Law can estimate fire radiative flux density:

<div align="center">
  <img src="https://latex.codecogs.com/svg.image?%20FRFD=%5Csigma(T_%7Bf%7D%5E%7B4%7D-T_%7Bb%7D%5E%7B4%7D)" alt="equation" />
</div>
<b>where:</b> 
<div align="center">
  <img src="https://latex.codecogs.com/svg.image?%5Cbegin%7Bmatrix%7D%5C%5CT_%7Bf%7D=%5Ctextrm%7BCalibrated%20temperature%20provided%20by%20sensor%7D%5C%5CT_%7Bb%7D=%5Ctextrm%7BAmbient%20temperature%20around%20the%20fire%7D%5C%5C%5Csigma=%5Ctextrm%7BStefan%20Boltzmann%20constant%7D%5Cend%7Bmatrix%7D" alt="equation" />
</div>

<br></br>

The time series of FRFD can be used to calculate the Fire Radiative Energy Density (FRED), a time integrated sum of the total radiant energy released by the fire:

<div align="center">
  <img src="https://latex.codecogs.com/svg.image?%20FRED=%5Csum_%7Bi%7D%5E%7Bn%7D0.5(FRFD_%7Bi%7D&plus;FRFD_%7Bi-1%7D)(t_%7Bi%7D-t_%7Bi-1%7D)" alt="equation" />
</div>

<b>where:</b> 
<div align = "center">
  <img src="https://latex.codecogs.com/svg.image?%5Cbegin%7Bmatrix%7D%5C%5Ct=%5Ctextrm%7BTime(s)%7D%5C%5CFRFD=%5Ctextrm%7BFire%20radiative%20flux%20density%20from%20each%20time%20series%20image%7D%5Cend%7Bmatrix%7D" alt="equation" />
</div>
<br></br>

<img src="https://github.com/amcfaddenGIS/FRED-Analyst/blob/main/Images/Trap_rule.png" width = "500" height = "325" align = "right" alt="FRFD Temproal Plot" title="FRFD Temproal Plot">


To the right is an FRFD time series that illustrates the calculation of FRED. This is formulated through a time series of satellite or aerial images. The X axis is the calculated FRFD, and the Y axis is the time (seconds) since imagery collection had begun. Each point that formulates the time series is an individual FRFD estimation. The light blue area shaded below the curve is the time integrated sum (FRED) below the FRFD time series. 



## **The ArcGIS Toolbox**



