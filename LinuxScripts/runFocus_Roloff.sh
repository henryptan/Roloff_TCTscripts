#!/bin/bash

echo "Watch the PSU ramp up, and click "LOCAL" when it reaches the set voltage to override the false compliance warning.\n Press ENTER to begin PSU Ramp Up and runFocus scan..."
read aa

compliance=0.00025
voltage=-100
axis="xyz"

while getopts "m:v:a:" flag; do
	case "${flag}" in 
		m) compliance="${OPTARG}" ;;
		v) voltage="${OPTARG}" ;;
		a) axis="${OPTARG}" ;;
	esac
done 

shift $((OPTIND - 1 ))
device_pos=$1

echo "compliance=$compliance"
echo "voltage=$voltage"
echo "axis=$axis"

echo "~/Desktop/TCT/RoloffLab/focusR -b n -a "average" -c 1 -v $voltage -m $compliance -e $axis -s Small $device_pos"

~/Desktop/TCT/RoloffLab/focusR -b n -a "average" -c 1 -v $voltage -m $compliance -e $axis -s Small $device_pos

~/Desktop/TCT/RoloffLab/focusR -p $device_pos

