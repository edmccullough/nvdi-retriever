import geopandas as gpd
import pandas as pd
import numpy as np
from osgeo import ogr
import gdal
import os


# Define input and output files
map_dir = "/home/ed/Maps/TriggRanch/TriggRanchMap/Topography"
inputraster = os.path.join(map_dir, "n35_w104_1arc_v3-clipped-slope.tif")
inputraster_units = "pct slope"
inputshape = os.path.join("/home/ed/Maps/TriggRanch/TriggPastures/TirggPasturesESRI", "TriggPastures.shp")
outputcsv = os.path.join(map_dir,"pasturedata.csv")
bins=[0, 5, 10, 15, 20, 25, 10000]   # used for gdal histogram

pasture_values = []
pasture_names = []
shapes = gpd.read_file(inputshape)
print(shapes)

# Create cropped output raster for pasture
for i in range(len(shapes)):
    layername = shapes.Name[i]
    print("Processing layer "+layername)
    outputraster =  os.path.join(map_dir, "slope_"+layername.replace(" ", "_").replace("/", "-")+".tif")
    print("Outputting to ",outputraster)
    try:
        os.remove(outputraster)
    except:
        pass
    command = "gdalwarp -cutline "+inputshape+" -cwhere \"Name = '"+layername+"'\" -crop_to_cutline -dstalpha "+inputraster+" "+outputraster
    os.system(command)
    dataset= gdal.Open(outputraster)
    Xsize = dataset.RasterXSize
    Ysize = dataset.RasterYSize
    band_count = dataset.RasterCount
    tif_array = np.zeros((band_count, Ysize, Xsize))
    for i in range(band_count):
        tif_array[i]  = np.array(dataset.GetRasterBand(i+1).ReadAsArray())
    print(tif_array.shape)

    tmplist=[]
    for x in range(Xsize):
        for y in range(Ysize):
            pixel_slope = tif_array[0,y,x]
            pixel_alpha = tif_array[1,y,x]
            # print(x,y, pixel_slope, pixel_alpha)
            if pixel_alpha > 1:
                # print("Non-masked pixel, slope = ", pixel_slope)
                tmplist.append(pixel_slope)
    print(len(tmplist))
    pasture_values.append(tmplist)
    pasture_names.append(layername)

gt = dataset.GetGeoTransform()
print(gt)

pasture_stats = np.zeros((4+len(bins)-1,len(pasture_values)))
pixel_area = (gt[1] * gt[5])/ -4046.8564224  # pixel dimensions in meters divided by 4046 m^2 / acre

for i in range(len(pasture_values)):
    pasture_stats[0,i] = np.mean(pasture_values[i])
    pasture_stats[1,i] = np.std(pasture_values[i])
    pasture_stats[2,i] = np.min(pasture_values[i])
    pasture_stats[3,i] = np.max(pasture_values[i])
    hist,foo = np.histogram(pasture_values[i], bins = bins)
    for j in range(len(bins)-1):
        pasture_stats[j+4,i] = hist[j] * pixel_area
print(bins)

histogram_labels = []
histogram_labels.append('Land area: <'+str(bins[1])+inputraster_units)
for i in range(len(bins)-3):
    histogram_labels.append('Land area:'+str(bins[i+1])+'-'+str(bins[i+2])+inputraster_units)
histogram_labels.append('Land area: >'+str(bins[len(bins)-2])+inputraster_units)

# Create dataframe using pasture and stats data and export to csv file
pasture_data = {'Pasture Names': pasture_names,
    'Mean': pasture_stats[0],
    'Std': pasture_stats[1],
    'Min': pasture_stats[2],
    'Max': pasture_stats[3]
    }
for i in range(len(histogram_labels)):
    pasture_data[histogram_labels[i]] = pasture_stats[i+4]

columns= ['Pasture Names', 'Mean','Std','Min','Max']
# ,histogram_labels[0],histogram_labels[1],histogram_labels[2],histogram_labels[3]]
for i in range(len(histogram_labels)):
    columns.append(histogram_labels[i])
df = pd.DataFrame(pasture_data, columns = columns)
print (df)
print("outputting to csv file at "+outputcsv)
df.to_csv(outputcsv, index = False, header=True)
