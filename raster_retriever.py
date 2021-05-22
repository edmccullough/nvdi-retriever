import os, glob
import json
import datetime as dt
import tarfile
from landsatxplore.api import API
from landsatxplore.earthexplorer import EarthExplorer
from osgeo import gdal, osr
from PIL import Image
import numpy as np
import keyring

# key variables
output_dir='/home/ed/Maps/TriggRanch/_Landsat'
ee_username = "edwardm@gmail.com"
x_min, x_max = 588461, 619129
y_min, y_max = 3922095, 3956347
XSize = 1022
YSize = 1142
latitude = 35.58
longitude = -103.85
end_date = dt.date.today()
start_date = dt.date(2021, 2, 1)
dataset="landsat_8_c1"
# https://pypi.org/project/landsatxplore/
# Landsat 7 ETM+ Collection 1 Level 1       landsat_etm_c1
# Landsat 7 ETM+ Collection 2 Level 1       landsat_etm_c2_l1
# Landsat 7 ETM+ Collection 2 Level 2       landsat_etm_c2_l2
# Landsat 8 Collection 1 Level 1            landsat_8_c1
# Landsat 8 Collection 2 Level 1            landsat_ot_c2_l1
# Landsat 8 Collection 2 Level 2            landsat_ot_c2_l2

def crop_remove_raster(inputraster):
    # outputraster =  os.path.join(landsat_dir, landsat_product_id+"_B"+str(band)+"_cropped.TIF")
    f_dir = os.path.dirname(inputraster)
    f_name, f_ext = os.path.splitext(os.path.basename(inputraster))
    outputraster =  os.path.join(f_dir, f_name+"_cropped"+f_ext)
    try:
        os.remove(outputraster)
    except:
        pass
    print("Crop in range "+str(x_min)+" "+str(y_min)+" "+str(x_max)+" "+str(y_max))
    command = "gdalwarp -te "+str(x_min)+" "+str(y_min)+" "+str(x_max)+" "+str(y_max)+" "+inputraster+" "+ outputraster
    os.system(command)
    os.remove(inputraster)

def extract_crop_remove_raster(zip_dir):
    # zip_dir is the directory containing the compressed file
    zip_list = glob.glob(os.path.join(zip_dir,'*.tar.gz'))
    try:
        zip_path = zip_list[0]   
        print("Extracting compressed file "+zip_path)
        tar = tarfile.open(zip_path, "r:gz")
        tar.extractall(zip_dir)
        tar.close()
    except:
        pass
    tifs = glob.glob(os.path.join(zip_dir,'*.TIF'))
    for tif in tifs:
        print(str(tif)," cropping starting now....")
        crop_remove_raster(tif)
    os.remove(zip_path)

def landsat_fetch():

    def query_landsat_downloads():
        print("Searching from "+str(start_date)+" to "+str(end_date))
        password = keyring.get_password("EarthExplorer", ee_username)
        api = API(ee_username, password)
        scenes = api.search(
            dataset=dataset,
            latitude=latitude,
            longitude=longitude,
            start_date=str(start_date),
            end_date=(str(end_date)),
            max_cloud_cover=10
        )
        print("Logging out of API...")
        api.logout()
        return scenes
        # print(f"{len(scenes)} scenes found:")
        # for scene in scenes:
        #     print(scene['acquisition_date'])

    def download_landsat_scene(landsat_product_id):
        print("Logging into EarthExplorer...")
        password = keyring.get_password("EarthExplorer", ee_username)
        ee = EarthExplorer(ee_username, password)
        print("Downloading "+landsat_product_id+".  Imagery aquired ", scene['acquisition_date'])
        ee.download(landsat_product_id, output_dir=landsat_dir)
        ee.logout()

    scenes = query_landsat_downloads()
    for i in range(len(scenes)):
        scene = scenes[i]
        landsat_product_id = scene['landsat_product_id']
        landsat_dir = os.path.join(output_dir,landsat_product_id)
        if os.path.exists(landsat_dir):
            print("Folder exists for landsat_product_id. Skipping download.")
        else:
            print("Downloading "+landsat_product_id)
            download_landsat_scene(landsat_product_id)
            print("Processing "+landsat_product_id)
            extract_crop_remove_raster(landsat_dir)

def tif_to_array(tif_path):
    dataset= gdal.Open(tif_path)
    band_count = dataset.RasterCount
    XSize = dataset.RasterXSize
    YSize = dataset.RasterYSize
    tif_array = np.zeros((band_count,YSize, XSize))
    for b in range(band_count):
        tif_array[b]  = np.array(dataset.GetRasterBand(b+1).ReadAsArray())
    return tif_array

def array_to_tif(tif_array, output_file, reference_tif):
    # array is 2D array to be converted into TIF file
    # output_file = os.path.join(landsat_dir, landsat_product_id+"_NVDI.TIF")
    
    # Convert NVDI matrix to tif file
    print("Converting NVDI matrix to GeoTiff file...")
    dataset = gdal.Open(reference_tif)
    wkt = dataset.GetProjection()
    driver = gdal.GetDriverByName("GTiff")
    band = dataset.GetRasterBand(1)
    gt = dataset.GetGeoTransform()
    XSize = tif_array.shape[1]
    YSize = tif_array.shape[0]
    # XSize = dataset.RasterXSize
    # YSize = dataset.RasterYSize
    dst_ds = driver.Create(output_file, XSize, YSize, 1, gdal.GDT_Int16)
    dst_ds.GetRasterBand(1).WriteArray(tif_array)     # write output raster
    dst_ds.GetRasterBand(1).SetNoDataValue(0)    # set nodata value
    dst_ds.SetGeoTransform(gt)  # set geotransform from dataset
    srs = osr.SpatialReference()    # set spatial reference of output raster
    srs.ImportFromWkt(wkt)
    dst_ds.SetProjection( srs.ExportToWkt() )
    ds = None       # close output raster dataset
    dst_ds = None    # close output raster dataset
    print("GeoTiff file created at"+output_file)

def nvdi_generator(nir_raster, red_raster, output_file="NULL"):
    nir_array = tif_to_array(nir_raster)[0]
    red_array = tif_to_array(red_raster)[0]
    # nir_array = np.array(nir_dataset.GetRasterBand(1).ReadAsArray())
    # red_array = np.array(red_dataset.GetRasterBand(1).ReadAsArray())
    XSize = nir_array.shape[1]
    YSize = nir_array.shape[0]
    if(XSize != red_array.shape[1] or YSize != red_array.shape[0]):
        print("Arrays are different shapes")

    # Initialize nvdi_array
    nvdi_array = np.zeros((YSize, XSize))
    nvdi_array = nvdi_array.astype('float32')
    print(nvdi_array.shape)

    # Calculate NVDI matrix
    print("Calculating NVDI matrix.....")
    for x in range(XSize):
        for y in range(YSize):
            try:
                red = red_array[y][x].astype('float32')
                nir = nir_array[y][x].astype('float32')
                nvdi_array[y][x] = (nir - red) / (nir + red) *10000.
                # print(min(max(nvdi_array[i][y][x],-10000),10000))
            except:
                # pass
                print("x = "+str(x)+"; y = "+str(y))
                print("nir = "+str(nir)+"; red = "+str(red))
    
    # Create tif (optional) and return array
    if(output_file != "NULL"):
        array_to_tif(nvdi_array, output_file, red_raster)
    return(nvdi_array)

