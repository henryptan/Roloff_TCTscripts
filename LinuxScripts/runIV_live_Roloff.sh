#! /bin/bash

temp=22C #-20C

DUT_device=$1
DUT_type="n"

echo "\nIs the cable connected to the right sensor? Return to continue..."
read aa
for i in `seq 1`
do
  name=${DUT_device}
  datafile=iv_${name}.txt

  echo ${name}

  # Start fresh so the live plot doesn't show data from a previous run
  rm -f ${datafile}

  # Launch the live plot in the background, pointed at the file
  # IVKeithleyR.py is about to create and write to
  ~/Desktop/TCT/RoloffLab/plotIV_live.py ${datafile} &
  PLOT_PID=$!

  # Run the actual IV scan in the foreground; the plot window updates
  # every couple seconds as new lines land in ${datafile}
  ~/Desktop/TCT/RoloffLab/IVKeithleyR.py -d ${name} -t $DUT_type

  # Scan finished - give the plot a moment to catch the final point,
  # then close the live plot window
  sleep 3
  ~/Desktop/TCT/RoloffLab/plotIVR.py ${datafile}
  ~/Desktop/TCT/source/plotIV.py ${datafile}
  kill ${PLOT_PID} 2>/dev/null
done
