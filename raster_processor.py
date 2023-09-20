#!/bin.python
# /home/ed/Maps/raster_processor.py
import numpy as np
import pandas as pd
import glob
import os
# import gdal
from osgeo import gdal, osr
import re
import datetime
from scipy.optimize import curve_fit


landsat_dir = '/home/ed/Maps/TriggRanch/_Landsat'
reference_tif = '/home/ed/Maps/TriggRanch/_Landsat/LC08_L1TP_032035_20210301_20210311_01_T1/LC08_L1TP_032035_20210301_20210311_01_T1_B1_cropped.TIF'
XSize = 1022
YSize = 1142
calcs = ["mean", "min", "max", "std", "deciduousity", "omega"]
scaling_factor = 10000
no_data_value = 0

# Get list of landsat files
def get_landsat_filelist(landsat_dir):
    tmplist=[]
    print("Checking in "+str(landsat_dir)+" led to these results: ")
    for dir_name in os.listdir(landsat_dir):
        print("dir_name = ",dir_name)
        if os.path.isdir(os.path.join(landsat_dir, dir_name)):
            print("adding to tmplist")
            tmplist.append(dir_name)
    # landsat_filelist = tmplist
    # (landsat_filelist)
    return tmplist


# def this_didnt_get_passed_anthing():
#     print(XSize, YSize)

# initialize arrays

landsat_filelist = get_landsat_filelist(landsat_dir)
file_count = len(landsat_filelist)
# print(landsat_filelist)

# Generate geotiff from array
def generate_geotiff_from_array(landsat_dir, landsat_product_id ,label, input_array):
    print("Generating Geotiff for ", label)
    dataset= gdal.Open(reference_tif)
    wkt = dataset.GetProjection()
    driver = gdal.GetDriverByName("GTiff")
    band = dataset.GetRasterBand(1)
    gt = dataset.GetGeoTransform()
    if not landsat_product_id.strip():
        output_file = os.path.join(landsat_dir, label +".TIF")
    else:
        output_file = os.path.join(landsat_dir, landsat_product_id, landsat_product_id + label +".TIF")
    dst_ds = driver.Create(output_file, XSize, YSize, 1, gdal.GDT_Int16)
    dst_ds.GetRasterBand(1).WriteArray(input_array)     #write output raster
    dst_ds.GetRasterBand(1).SetNoDataValue(no_data_value)    #set nodata value as zero
    dst_ds.SetGeoTransform(gt)  #set geotransform for new raster based on dataset
    srs = osr.SpatialReference()    #set spatial reference of output raster
    srs.ImportFromWkt(wkt)
    dst_ds.SetProjection( srs.ExportToWkt() )
    ds = None       #Close output raster dataset
    dst_ds = None    #Close output raster dataset
    print("GeoTiff file created at "+output_file)

# Calculate NDVI matrix and create TIF file
def ndvi_tif_generator(landsat_dir):
    landsat_filelist = get_landsat_filelist(landsat_dir)
    ndvi_array = np.zeros((YSize, XSize)) #initialize ndvi_array
    print("Calculating NDVI matrix for "+str(file_count)+" files...")
    for i in range(file_count):
    # for i in range(1,2):
        print("Calculating NDVI matrix for file "+str(i)+" of "+str(file_count))
        landsat_product_id = os.path.basename(landsat_filelist[i])
        
        print("Loading "+landsat_product_id)
        qa_raster= gdal.Open(os.path.join(landsat_dir, landsat_product_id , landsat_product_id +"_BQA_cropped.TIF"))
        qa_array = np.array(qa_raster.GetRasterBand(1).ReadAsArray())
        red_raster= gdal.Open(os.path.join(landsat_dir, landsat_product_id , landsat_product_id +"_B4_cropped.TIF"))
        red_array = np.array(red_raster.GetRasterBand(1).ReadAsArray())
        nir_raster= gdal.Open(os.path.join(landsat_dir, landsat_product_id , landsat_product_id +"_B5_cropped.TIF"))
        nir_array = np.array(nir_raster.GetRasterBand(1).ReadAsArray())

        XSize = nir_array.shape[1]
        YSize = nir_array.shape[0]
        for x in range(XSize):
            for y in range(YSize):
                try:
                    qa = qa_array[y][x]
                    red = red_array[y][x].astype('float32')
                    nir = nir_array[y][x].astype('float32')
                    ndvi = (nir - red) / (nir + red) *scaling_factor

                    if(qa == 2720): #means that the pixel quality is OK https://www.usgs.gov/landsat-missions/landsat-collection-1-level-1-quality-assessment-band
                        ndvi_array[y][x] = ndvi
                        # print("Writing ndvi = "+str(ndvi)+" to x = "+str(x)+"; y = "+str(y))
                    else:
                        ndvi_array[y][x] = no_data_value
                        # print("Pixel not clear with code "+str(qa)+". Writing "+no_data_value+" (no data) to x = "+str(x)+"; y = "+str(y))
                except:
                    print("Exception: nir = "+str(nir)+"; red = "+str(red)+"; ndvi = "+str(ndvi)+"; qa = "+str(qa)+"; x = "+str(x)+"; y = "+str(y))
        generate_geotiff_from_array(landsat_dir= landsat_dir,landsat_product_id=landsat_product_id,label="_NDVI_cropped", input_array=ndvi_array)

    return ndvi_array

# Calculate NDWI matrix and create TIF file
def ndwi_tif_generator(landsat_dir):

# Load NDVI images into array
def ndvi_tif_to_array(landsat_dir):
    print("Loading NDVI images...")
    landsat_filelist = get_landsat_filelist(landsat_dir)
    file_count = len(landsat_filelist)
    date_array = np.zeros((file_count,3)).astype('int64')
    raster_array = np.zeros((file_count,YSize, XSize))
    for i in range(file_count):
        landsat_product_id = os.path.basename(landsat_filelist[i])
        print("Loading"+landsat_product_id)
        dataset= gdal.Open(os.path.join(landsat_dir, landsat_product_id , landsat_product_id +"_NDVI_cropped.TIF"))
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

    print("Populate tif calc array....")
    tif_calc_array = np.zeros((file_count,len(calcs)+3)).astype('float32')
    print(tif_calc_array.shape)
    for i in range(file_count):
        print("Tif number",i)
        tif_calc_array[i,0]= date_array[i,0]
        tif_calc_array[i,1]= date_array[i,1]
        tif_calc_array[i,2]= date_array[i,2]
        tif_calc_array[i,3]= np.mean(np.concatenate(raster_array[i])) / scaling_factor
        tif_calc_array[i,4]= np.std(np.concatenate(raster_array[i])) / scaling_factor
        tif_calc_array[i,5]= np.min(np.concatenate(raster_array[i])) / scaling_factor
        tif_calc_array[i,6]= np.max(np.concatenate(raster_array[i])) / scaling_factor

    np.savetxt('tif_calcs.csv', tif_calc_array, delimiter=',', fmt='%1.3f', header="Year, Month, DayOfYear, Mean, Std, Min, Max")

    return raster_array, date_array

# Calculate deciduosity of a given pixel by fitting an annual harmonic function to the time series and returning magnitude and angle
def deciduosity(pixel_timeseries, doy_values):
    # Annual harmonic function
    def annual_harmonic(t, a0, a1, b1, omega):
        return a0 + a1 * np.cos(omega * t) + b1 * np.sin(omega * t)
    try:
        popt, _ = curve_fit(annual_harmonic, doy_values, pixel_timeseries, p0=(0.5, 0.5, 0.5, 2 * np.pi / 365))
        a0, a1, b1, omega = popt
        magnitude = np.sqrt(a1**2 + b1**2)  # The magnitude of the annual variation is given by sqrt(a1^2 + b1^2)
        return magnitude, omega
    except:
        return np.nan, np.nan

# Generate pixel calc images
def ndvi_pixel_calculator(landsat_dir):
    raster_array, date_array = ndvi_tif_to_array(landsat_dir=landsat_dir)
    print("Populate pixel calc array...")
    pixel_calc_array = np.zeros((len(calcs),YSize, XSize))
    # for x in range(1,100):   # for testing purposes with small sample
    #     for y in range(1,100):
    for x in range(XSize):
        for y in range(YSize):
            print(f'x={x},y={y}')
            pixel_raw_values = raster_array[:,y,x] / scaling_factor
            doy_values = date_array[:,2]

            mask = pixel_raw_values != no_data_value  # Filtering out "no data" values
            pixel_timeseries = pixel_raw_values[mask]
            doy_timeseries = doy_values[mask]

            pixel_calc_array[0,y,x]= np.mean(pixel_timeseries) * scaling_factor #mean
            pixel_calc_array[1,y,x]= np.min(pixel_timeseries) * scaling_factor  #min
            pixel_calc_array[2,y,x]= np.max(pixel_timeseries) * scaling_factor #max
            pixel_calc_array[3,y,x]= np.std(pixel_timeseries) * scaling_factor #standard deviation

            pixel_deciduosity, omega= deciduosity(pixel_timeseries=pixel_timeseries, doy_values=doy_timeseries) #deciduosity and phase angle
            # print(pixel_deciduosity, omega)
            pixel_calc_array[4,y,x]= pixel_deciduosity * scaling_factor
            pixel_calc_array[5,y,x]= omega * scaling_factor
            # print(pixel_calc_array[:,y,x])

    print("Converting NDVI matrix to GeoTiff file...")
    for i in range(len(calcs)):
        generate_geotiff_from_array(landsat_dir= landsat_dir,landsat_product_id="", label='NDVI_'+calcs[i], input_array=pixel_calc_array[i])
    return pixel_calc_array

# Calculate expected NDVI value for a given pixel on a given day of year given mean, magnitude, and 
def expected_ndvi(doy, mean, magnitude, omega, phase_angle):
    return mean + magnitude * np.cos(omega * doy + phase_angle)











# def correlate_ndvi_dem(ndvi_file, dem_file, output_csv):
#     # Load NDVI raster
#     ndvi_ds = gdal.Open(ndvi_file)
#     ndvi_geotransform = ndvi_ds.GetGeoTransform()
#     ndvi_proj = ndvi_ds.GetProjection()
    
#     # Load DEM raster
#     dem_ds = gdal.Open(dem_file)
    
#     # Resample DEM to match NDVI resolution
#     resampled_dem = gdal.Warp('', dem_file, format='MEM', xRes=ndvi_geotransform[1], yRes=-ndvi_geotransform[5], resampleAlg='bilinear')
#     dem_array = resampled_dem.ReadAsArray()
    
#     # Here I assume you've pre-processed the NDVI data as you've done in your previous script
#     # And have the raster_array (NDVI time series) and date_array (DOY values)
#     raster_array = ... # Your pre-processed NDVI time series data
#     date_array = ... # Corresponding DOY values
#     doy_values_all = date_array[:, 2]
    
#     data = {'Omega': [], 'Elevation': []}
#     for x in range(raster_array.shape[2]):
#         for y in range(raster_array.shape[1]):
#             ndvi_time_series_all = raster_array[:, y, x]
#             mask = ndvi_time_series_all != 0
#             ndvi_time_series = ndvi_time_series_all[mask]
#             doy_values = doy_values_all[mask]
            
#             omega = compute_omega(ndvi_time_series, doy_values)
            
#             elevation = dem_array[y, x]
            
#             data['Omega'].append(omega)
#             data['Elevation'].append(elevation)
    
#     df = pd.DataFrame(data)
#     df.to_csv(output_csv, index=False)


# def correlate_ndvi_dem(ndvi_file, dem_file, output_csv):
#     # Load NDVI raster
#     ndvi_ds = gdal.Open(ndvi_file)
#     ndvi_geotransform = ndvi_ds.GetGeoTransform()
#     ndvi_proj = ndvi_ds.GetProjection()
    
#     # Load DEM raster
#     dem_ds = gdal.Open(dem_file)
    
#     # Resample DEM to match NDVI resolution
#     resampled_dem = gdal.Warp('', dem_file, format='MEM', xRes=ndvi_geotransform[1], yRes=-ndvi_geotransform[5], resampleAlg='bilinear')
#     dem_array = resampled_dem.ReadAsArray()
    
#     # Here I assume you've pre-processed the NDVI data as you've done in your previous script
#     # And have the raster_array (NDVI time series) and date_array (DOY values)
#     raster_array = ... # Your pre-processed NDVI time series data
#     date_array = ... # Corresponding DOY values
#     doy_values_all = date_array[:, 2]
    
#     data = {'Omega': [], 'Elevation': []}
#     for x in range(raster_array.shape[2]):
#         for y in range(raster_array.shape[1]):
#             ndvi_time_series_all = raster_array[:, y, x]
#             mask = ndvi_time_series_all != 0
#             ndvi_time_series = ndvi_time_series_all[mask]
#             doy_values = doy_values_all[mask]
            
#             omega = compute_omega(ndvi_time_series, doy_values)
            
#             elevation = dem_array[y, x]
            
#             data['Omega'].append(omega)
#             data['Elevation'].append(elevation)
    
#     df = pd.DataFrame(data)
#     df.to_csv(output_csv, index=False)

# # Example usage
# correlate_ndvi_dem('path_to_ndvi.tif', 'path_to_dem.tif', 'output.csv')
# In the script above:

# The compute_omega function is responsible for extracting the harmonic coefficient (omega) from a given NDVI time series.
# The correlate_ndvi_dem function handles the main tasks, which involve loading the rasters, resampling the DEM, computing the harmonic coefficients, and writing the results to a CSV file.
# After running the script, the resulting CSV will have two columns: 'Omega' and 'Elevation', which you can then use to graph and analyze the correlation between them.

# correlate_ndvi_dem('path_to_ndvi.tif', 'path_to_dem.tif', 'output.csv')


# ndvi_tif_generator(landsat_dir=landsat_dir)
# ndvi_pixel_calculator(landsat_dir=landsat_dir)
# this_didnt_get_passed_anthing()
