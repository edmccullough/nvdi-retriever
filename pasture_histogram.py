import geopandas as gpd
import pandas as pd
import numpy as np
from osgeo import ogr
import gdal
import os


# Define input and output files
map_dir = "/home/ed/Maps/TriggRanch/TriggRanchMap/Topography"
inputshape = os.path.join("/home/ed/Maps/TriggRanch/TriggPastures/TirggPasturesESRI", "TriggPastures.shp")
inputraster = os.path.join(map_dir, "n35_w104_1arc_v3-clipped-slope.tif")
pasture_values = []
pasture_names = []
bins=[0, 10, 20, 30]

#geopandas version
shapes = gpd.read_file(inputshape)
print(shapes)
# print(len(shapes))
# list(shapes.columns.values)
# [u'dip', u'dip_dir', u'cosa', u'sina', 'geometry']

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
    # band_count = 2
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

pasture_stats = np.zeros((4+4,len(pasture_values)))
pixel_area = 243243 / 55000

for i in range(len(pasture_values)):
    pasture_stats[0,i] = np.mean(pasture_values[i])
    pasture_stats[1,i] = np.std(pasture_values[i])
    pasture_stats[2,i] = np.min(pasture_values[i])
    pasture_stats[3,i] = np.max(pasture_values[i])
    hist,foo = np.histogram(pasture_values[i], bins = bins)
    pasture_stats[4,i] = hist[0] / pixel_area
    pasture_stats[5,i] = hist[1] / pixel_area
    pasture_stats[6,i] = hist[2] / pixel_area
    # pasture_stats[7,i] = hist[3]
    # print(pasture_names[i])

print(bins)

pasture_data = {'Pasture Names': pasture_names,
    'Mean': pasture_stats[0],
    'Std': pasture_stats[1],
    'Min': pasture_stats[2],
    'Max': pasture_stats[3],
    'Histogram0': pasture_stats[4],
    'Histogram1': pasture_stats[5],
    'Histogram2': pasture_stats[6],
    'Histogram3': pasture_stats[7]
    # 'Histogram': np.histogram(pasture_values, bins = bins)
    # 'Pasture Values': pasture_values
    }

df = pd.DataFrame(pasture_data, columns= ['Pasture Names', 'Mean','Std','Min','Max','Histogram0','Histogram1','Histogram2','Histogram3'])
print (df)
df.to_csv(os.path.join(map_dir,"pasturedata.csv"), index = False, header=True)

