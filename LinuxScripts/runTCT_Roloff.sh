#! /bin/bash

acq=1
temp=22
channel_DUT=1
intensity=34.0
DUT_compliance=0.0002

DUT_device="FNALboard_rightLGAD"
DUT_type="n"
DUT_init_voltage=0
DUT_end_voltage=-101
DUT_step=-3
bias_voltage=-100
DUT_shiftPos=-5000
multi_channel=false

while getopts "c:m:n:v:i:f:s:M" flag; do
	case "${flag}" in
		c) channel_DUT="${OPTARG}" ;;
		m) DUT_compliance="${OPTARG}" ;;
		n) DUT_device="${OPTARG}" ;;
		v) bias_voltage="${OPTARG}" ;;
		i) DUT_init_voltage="${OPTARG}" ;;
		f) DUT_end_voltage="${OPTARG}" ;;
		s) DUT_step="${OPTARG}" ;;
		M) multi_channel=true ;;
	esac
done

if [ "$multi_channel" = true ]; then 
	channels="$channel_DUT"
else
	channels="$(echo "$channel_DUT" | cut -d',' -f1)"
fi 

echo "Oscilloscope Channel for Sensor: Channel $channel_DUT"
if [ "$multi_channel" = true ]; then 
	echo "Multi-channel mode is ON: acquiring channels $channels"
else 
	echo "Multi-channel mode is OFF: acquiring channel $channels"
fi 
echo "Compliance is set to $DUT_compliance A"
echo "Bias voltage for electronic noise is $bias_voltage V"
echo "The sweep will start at $DUT_init_voltage V" 
echo "The sweep will end at $DUT_end_voltage V"
echo "The step size is set at $DUT_step V"

shift $((OPTIND - 1 ))
DUT_pos=$1

echo "\nAre the cables connected to the output channel on the circuit board? Return to continue..."
read aa

echo "\nReading selected sensor..."
~/Desktop/TCT/RoloffLab/focusR -p $DUT_pos
~/Desktop/TCT/RoloffLab/movetopositionR -e y -d $DUT_shiftPos
echo "Reading electronic noise for the DUT..."
~/Desktop/TCT/RoloffLab/TCTR -b $DUT_type -t $temp -f "electronicNoise_${DUT_device}.bin" -x -a "average" -n $acq -v $bias_voltage -c $channels -m $DUT_compliance
~/Desktop/TCT/RoloffLab/TCTR -z
~/Desktop/TCT/RoloffLab/focusR -p $DUT_pos
for DUT_voltage in `seq $DUT_init_voltage $DUT_step $DUT_end_voltage`
do
  echo "Reading DUT signal at voltage=$DUT_voltage ..."
  ~/Desktop/TCT/RoloffLab/TCTR -b $DUT_type -t $temp -f $DUT_device -x -a "average" -n $acq -v $DUT_voltage -c $channels -i $intensity -m $DUT_compliance
done

~/Desktop/TCT/RoloffLab/TCTR -z 
#echo "\nPlug in Ref filter into Ref amp and Ref amp into scope Ch4. Ramp up Ref voltage. Press return to continue..."
#read aa
