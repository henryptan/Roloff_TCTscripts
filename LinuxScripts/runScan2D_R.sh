#!/bin/bash

echo "Have you changed the channel cable? Return to continue..."
read aa 

device_pos=$1
compliance="2.5e-4"
device_type="n"
channel=${2:-"1 3 4"}  # Specify all target oscilloscope channels separated by space, e.g. "1 2 3"
voltage=-100
axis="xy"
size="Fine"

# Build a channel -> sensor name mapping so that, when multiple sensors are
# scanned at the same time (one sensor per oscilloscope channel), each
# channel's data can later be re-aligned to the correct sensor in
# sensors.txt by analyzeScan2DR.py.
echo ""
echo "Enter the sensor name (as listed in sensors.txt, e.g. First, Second, Ref...)"
echo "connected to each channel being scanned."
> channel_map.txt
for ch in $channel; do
  read -p "  Sensor on channel $ch: " sensor_name
  echo "${ch}:${sensor_name}" >> channel_map.txt
done
echo "Saved channel-to-sensor mapping to channel_map.txt:"
cat channel_map.txt
echo ""

~/Desktop/TCT/RoloffLab/scan2DR.py -b $device_type -a "average" -c $channel -v $voltage -m $compliance -e $axis -s $size $device_pos

~/Desktop/TCT/RoloffLab/focusR -p $1
