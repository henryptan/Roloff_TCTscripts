#! /bin/bash

# Defaults
channel="1"
compliance=0.0002
device="TCTpos"
bulk="n"
bias_voltage=-100
num_acq=1
num_avg=512
intensity=34.0
temp=22
laser_x=""
laser_y=""

while getopts "c:m:n:b:v:a:g:i:t:X:Y:" flag; do
	case "${flag}" in
		c) channel="${OPTARG}" ;;
		m) compliance="${OPTARG}" ;;
		n) device="${OPTARG}" ;;
		b) bulk="${OPTARG}" ;;
		v) bias_voltage="${OPTARG}" ;;
		a) num_acq="${OPTARG}" ;;
		g) num_avg="${OPTARG}" ;;
		i) intensity="${OPTARG}" ;;
		t) temp="${OPTARG}" ;;
		X) laser_x="${OPTARG}" ;;
		Y) laser_y="${OPTARG}" ;;
	esac
done

echo "Channel(s): $channel"
echo "Bias voltage: $bias_voltage V (compliance $compliance A)"
echo "Acquisitions (bin files per channel): $num_acq"
echo "Waveforms averaged per acquisition: $num_avg"

extra=()
if [ -n "$laser_x" ] && [ -n "$laser_y" ]; then
	extra=( -X "$laser_x" -Y "$laser_y" )
fi

~/Desktop/TCT/RoloffLab/TCTposR.py -b "$bulk" -t "$temp" -f "$device" \
	-v "$bias_voltage" -c "$channel" -i "$intensity" -m "$compliance" \
	-n "$num_acq" -g "$num_avg" "${extra[@]}"
