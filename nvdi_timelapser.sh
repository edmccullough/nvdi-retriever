#!/bin/bash
# nvdi_timelapser.sh [nvdi_path]

nvdi_path="/home/ed/Maps/TriggRanch/_Landsat/nvdi/"
# cp /home/ed/Maps/TriggRanch/_Landsat/*/*NVDI.TIF $path

frame_rate=10     # number of frames displayed per second
# #start_hour=$((`python3 sunrise.py` - 1))      # timelapse movie starts at this hour

mkdir -p $nvdi_path/timelapse
rm $nvdi_path/timelapse/timelapse.mov && echo Removed existing timelapse.mov
rm $nvdi_path/timelapse/output.avi && echo Removed existing output.avi
echo Searching in $nvdi_path
for i in $(ls $nvdi_path/*_NVDI.TIF); do
    base_filename=$(echo $i | sed 's/.*\///' | cut -d "." -f 1)
    convert $i $base_filename.png
    # gdal_translate -outsize 4096 4096 -of PNG -ot UInt16 -scale 1638.991 2577.040 0 65535 "GDAL_IMG_2_GeoTIFF.tif" "GDAL_IMG_2_GeoTIFF.png"
    # gdal_translate -of PNG -ot UInt16 -scale 32.53501 767.4913 0 65535 goes16.abi-2019.0902.1510-C01_1km.tif k.png
    
    # add date and time to image
    acquisition_date=$(echo $base_filename | cut -d "_" -f 4)
    year=$(echo $acquisition_date | cut -b 1-4)
    month=$(echo $acquisition_date | cut -b 5-6)
    day=$(echo $acquisition_date | cut -b)
    printday=$($year+" "+$month+" "+"$day")
    echo $printday
    convert $i -gravity center -fill white -font fixed -pointsize 44 -style Italic -annotate +0+420  $printday $path/timelapse/$i && echo Date added 
    # convert $i -gravity center -fill white -font fixed -pointsize 88 -style Italic -annotate +0+340 $timeofday $path/timelapse/$i && echo Time added 
done

# make timelapse
cd $nvdi_path/
ffmpeg -y -r $frame_rate -pattern_type glob -i '*.png' -c:v copy output.avi 
ffmpeg -y -i "output.avi" -acodec libmp3lame -ab 192 "timelapse.mov" && echo Time lapse video created at $path
