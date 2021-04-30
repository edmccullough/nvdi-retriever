import os
import json
import datetime as dt
import tarfile
# import geopandas as gpd
from landsatxplore.api import API
from landsatxplore.earthexplorer import EarthExplorer
from osgeo import gdal, osr
from PIL import Image
import numpy as np
import glob # only used for troubleshooting
import keyring

output_dir='/home/ed/Maps/TriggRanch/_Landsat'
end_date = dt.date.today()
start_date = dt.date(2021, 2, 1)
# location="35.58541 -103.83197" # center of ranch
print("Searching from "+str(start_date)+" to "+str(end_date))

latitude = 35.58
longitude = -103.85
username = "edwardm@gmail.com"
# https://pypi.org/project/landsatxplore/
# Landsat 7 ETM+ Collection 1 Level 1   landsat_etm_c1
# Landsat 7 ETM+ Collection 2 Level 1   landsat_etm_c2_l1
# Landsat 7 ETM+ Collection 2 Level 2   landsat_etm_c2_l2
# Landsat 8 Collection 1 Level 1            landsat_8_c1
# Landsat 8 Collection 2 Level 1            landsat_ot_c2_l1
# Landsat 8 Collection 2 Level 2            landsat_ot_c2_l2
dataset="landsat_8_c1"


# # Initialize a new API instance and search for Landsat TM scenes
password = keyring.get_password("EarthExplorer", username)
api = API(username, password)
scenes = api.search(
    dataset=dataset,
    latitude=latitude,
    longitude=longitude,
    start_date=str(start_date),
    end_date=(str(end_date)),
    max_cloud_cover=10
)

XSize = 1022
YSize = 1142

print(f"{len(scenes)} scenes found.")
for scene in scenes:
    print(scene['acquisition_date'])

# Initialize nvdi_array
nvdi_array = np.zeros((len(scenes),YSize, XSize))
nvdi_array = nvdi_array.astype('float32')

# Process the result
for i in range(len(scenes)):
    scene = scenes[i]
    landsat_product_id = scene['landsat_product_id']
    print(landsat_product_id)
    landsat_dir = os.path.join(output_dir,landsat_product_id)
    zip_path = os.path.join(landsat_dir, landsat_product_id+".tar.gz")
    # print("zip_path = "+zip_path)
    # print("landsat_dir = "+landsat_dir)

    # Download from EarthExplorer
    if os.path.exists(landsat_dir):
        print("Folder exists for landsat_product_id. Skipping download.")
    else:
        print("Logging into EarthExplorer...")
        password = keyring.get_password("EarthExplorer", username)
        ee = EarthExplorer(username, password)
        print("Downloading "+landsat_product_id+".  Imagery aquired ", scene['acquisition_date'])
        ee.download(landsat_product_id, output_dir=landsat_dir)
        ee.logout()
    
    # Extract tar.gz file and crop each band
    sample_cropped = os.path.join(landsat_dir, landsat_product_id+"_B1_cropped.TIF")
    if os.path.exists(sample_cropped):
        print("Cropped tif exists.  Skipping extract and crop.")
    else:
        print("Extracting compressed file "+zip_path)
        tar = tarfile.open(zip_path, "r:gz")
        tar.extractall(landsat_dir)
        tar.close()
        x_min, x_max = 588461, 619129
        y_min, y_max = 3922095, 3956347
        print("Crop in range "+str(x_min)+" "+str(y_min)+" "+str(x_max)+" "+str(y_max))
        bands = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 'QA']
        for band in bands:
        # for band in range (1,12):
            print(landsat_product_id+"_B"+str(band)+".TIF cropping starting now....")
            inputraster =  os.path.join(landsat_dir, landsat_product_id+"_B"+str(band)+".TIF")
            outputraster =  os.path.join(landsat_dir, landsat_product_id+"_B"+str(band)+"_cropped.TIF")
            try:
                os.remove(outputraster)
            except:
                pass
            command = "gdalwarp -te "+str(x_min)+" "+str(y_min)+" "+str(x_max)+" "+str(y_max)+" "+inputraster+" "+ outputraster
            os.system(command)
            os.remove(inputraster)
        os.remove(zip_path)

    # Convert tif to array
    bands = [1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 'QA']
    dataset= gdal.Open(sample_cropped)
    sample_array = np.array(dataset.GetRasterBand(1).ReadAsArray())

    landsat_array = np.zeros((len(bands),YSize, XSize))
    for i in range(len(bands)):
        print(bands[i])
        dataset= gdal.Open(os.path.join(landsat_dir, landsat_product_id+"_B"+str(bands[i])+"_cropped.TIF"))
        landsat_array[i]  = np.array(dataset.GetRasterBand(1).ReadAsArray())
        print(np.min(np.concatenate(landsat_array[i])))
        print(np.max(np.concatenate(landsat_array[i])))
        # print(np.mean(np.concatenate(landsat_array)))

    # Calculate NVDI matrix
    print("Calculating NVDI matrix.....")
    for x in range(XSize):
        for y in range(YSize):
            try:
                b4 = landsat_array[3][y][x].astype('int16')
                b5 = landsat_array[4][y][x].astype('int16')
                num = b5 - b4
                den = b5 + b4
                nvdi_array[i][y][x] = num / den *10000.
                print(min(max(nvdi_array[i][y][x],-1),1))
            except:
                print ("b4 = "+str(b4)+"; b5 = "+str(b5)+"; num = "+str(num)+"; den = "+str(den)+"; NVDI = "+str(nvdi_array[y][x]))
    # nvdi_array *= 10000.
    # nvdi_array = nvdi_array.astype('int16')
    print(nvdi_array[i])
    # print("Shape, Element Count, Sum, Min, Max, Ave")
    # print(nvdi_array.shape)
    # print(np.concatenate(nvdi_array).shape)
    # print(np.sum(np.concatenate(nvdi_array)))
    # print(np.min(np.concatenate(nvdi_array)))
    # print(np.max(np.concatenate(nvdi_array)))
    # print(np.mean(np.concatenate(nvdi_array)))

    # Convert NVDI matrix to tif file
    print("Converting NVDI matrix to GeoTiff file...")
    wkt = dataset.GetProjection()
    driver = gdal.GetDriverByName("GTiff")
    band = dataset.GetRasterBand(1)
    gt = dataset.GetGeoTransform()
    output_file = os.path.join(landsat_dir, landsat_product_id+"_NVDI.TIF")
    dst_ds = driver.Create(output_file, XSize, YSize, 1, gdal.GDT_Int16)
    dst_ds.GetRasterBand(1).WriteArray( nvdi_array[i] )     #writting output raster
    dst_ds.GetRasterBand(1).SetNoDataValue(0)    #setting nodata value
    dst_ds.SetGeoTransform(gt)
    srs = osr.SpatialReference()    # setting spatial reference of output raster
    srs.ImportFromWkt(wkt)
    dst_ds.SetProjection( srs.ExportToWkt() )
    ds = None       #Close output raster dataset
    dst_ds = None    #Close output raster dataset
    print("GeoTiff file created at"+output_file)


# Log out of api
print("Logging out of API...")
api.logout()

