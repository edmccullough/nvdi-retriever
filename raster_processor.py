#!/bin.python
# /home/ed/Maps/raster_processor.py
import numpy as np
import glob
import os
# import gdal
from osgeo import gdal, osr
import re
import datetime

landsat_dir = '/home/ed/Maps/TriggRanch/_Landsat'
XSize = 1022
YSize = 1142
calcs = ["mean", "std", "min", "max"]


# landsat_filelist = glob.glob(os.path.join(landsat_dir,'*'))
tmplist=[]
for dir_name in os.listdir(landsat_dir):
    print("dir_name = ",dir_name)
    if os.path.isdir(os.path.join(landsat_dir, dir_name)):
        print("adding to tmplist")
        tmplist.append(dir_name)
    # if not os.path.isdir(dir_name):
    #     print(dir_name)
    #     landsat_filelist.remove(dir_name)
landsat_filelist = tmplist


    # num=int(input("Enter number of players: "))
    # tmplist=[]
    # for _ in range(num):
    #     pl=input("Enter name: " )
    #     tmplist.append(pl)

    # print(tmplist)


print("landsat_filelist")
print(landsat_filelist)
file_count = len(landsat_filelist)
date_array = np.zeros((file_count,3)).astype('int64')
raster_array = np.zeros((file_count,YSize, XSize))
pixel_calc_array = np.zeros((len(calcs),YSize, XSize))
tif_calc_array = np.zeros((file_count,len(calcs)+3)).astype('float32')


# Load NVDI images into array
print("Loading NVDI images...")
for i in range(file_count):
    landsat_product_id = os.path.basename(landsat_filelist[i])
    print("Loading"+landsat_product_id)
    dataset= gdal.Open(os.path.join(landsat_dir, landsat_product_id , landsat_product_id +"_NVDI.TIF"))
    acq_date_string = re.split("[_]", landsat_product_id)[-4]
    acq_date = datetime.datetime.strptime(acq_date_string, "%Y%m%d")
    acq_year = acq_date.strftime("%Y")
    acq_month = acq_date.strftime("%m")
    acq_day = acq_date.strftime("%d")
    acq_day_of_year = acq_date.strftime("%j")
    print(acq_year, acq_month, acq_day)
    print(acq_date.strftime("%Y-%m-%d"))
    date_array[i,0] = int(acq_year)
    date_array[i,1] = int(acq_month)
    date_array[i,2] = int(acq_day_of_year)
    raster_array[i] = np.array(dataset.GetRasterBand(1).ReadAsArray())


# Calculate metrics by date and save as CSV
print("Populate tif calc array....")
print(tif_calc_array.shape)
for i in range(file_count):
    print("Tif number",i)
    tif_calc_array[i,0]= date_array[i,0]
    tif_calc_array[i,1]= date_array[i,1]
    tif_calc_array[i,2]= date_array[i,2]
    tif_calc_array[i,3]= np.mean(np.concatenate(raster_array[i])) / 10000.
    tif_calc_array[i,4]= np.std(np.concatenate(raster_array[i])) / 10000.
    tif_calc_array[i,5]= np.min(np.concatenate(raster_array[i])) / 10000.
    tif_calc_array[i,6]= np.max(np.concatenate(raster_array[i])) / 10000.

np.savetxt('tif_calcs.csv', tif_calc_array, delimiter=',', fmt='%1.3f', header="Year, Month, DayOfYear, Mean, Std, Min, Max")
# np.savetxt("tif_calcs.csv", np.dstack((np.arange(1, arr.size+1),arr))[0],"%d,%d",header="Id,Values")


# Generate pixel calc images
print("Populate pixel calc array...")
for x in range(XSize):
    for y in range(YSize):
        print(x,y)
        pixel_calc_array[0,y,x]= np.mean(raster_array[:,y,x])
        pixel_calc_array[1,y,x]= np.std(raster_array[:,y,x])
        pixel_calc_array[2,y,x]= np.min(raster_array[:,y,x])
        pixel_calc_array[3,y,x]= np.max(raster_array[:,y,x])
print("Converting NVDI matrix to GeoTiff file...")
for i in range(len(calcs)):
    print("Generating Geotiff for ", calcs[i])
    wkt = dataset.GetProjection()
    driver = gdal.GetDriverByName("GTiff")
    band = dataset.GetRasterBand(1)
    gt = dataset.GetGeoTransform()
    output_file = os.path.join(landsat_dir, "LC08_L1TP_032035_NVDI_"+ calcs[i] +".TIF")
    dst_ds = driver.Create(output_file, XSize, YSize, 1, gdal.GDT_Int16)
    dst_ds.GetRasterBand(1).WriteArray(pixel_calc_array[i])     #writting output raster
    dst_ds.GetRasterBand(1).SetNoDataValue(0)    #setting nodata value
    dst_ds.SetGeoTransform(gt)
    srs = osr.SpatialReference()    # setting spatial reference of output raster
    srs.ImportFromWkt(wkt)
    dst_ds.SetProjection( srs.ExportToWkt() )
    ds = None       #Close output raster dataset
    dst_ds = None    #Close output raster dataset
    print("GeoTiff file created at"+output_file)
