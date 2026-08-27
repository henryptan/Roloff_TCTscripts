#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""
Reads a single TCT .bin waveform file (and, optionally, an electronic-noise
.bin file) and produces:

  - A single voltage-vs-time figure of the processed signal (<prefix>_waveform.png)
  - A CSV of time (shifted so the trace starts at t = 0) and voltage
    (<prefix>_waveform.csv)

This reuses the exact same processing steps as analyzeDataR.py
(pedestal removal -> electronic-noise subtraction -> averaging -> signal cut),
so the trace plotted/exported here matches what that script uses internally to
focus on the signal window and compute charge.

Usage:
  ./plotWaveformR.py -f scan2D_First_ch1_x0_y0.bin -n electronicNoise_ch1.bin -b n
  ./plotWaveformR.py -f scan2D_First_ch1_x0_y0.bin -b n   (no noise subtraction)
"""

import argparse
import csv
import os.path
import numpy as np
import matplotlib
matplotlib.use( "Agg" )
import pylab

from TCTData import TCTData
from analyzeDataR import ( getData, convertAndShiftData, removeElectronicNoise,
                            averageTheData, cutData, plot_parameters )


def buildAverageTrace( filename, noiseFile, bulk, cut = "signal" ):
  """Run the file through the same pedestal / noise-subtraction / averaging
  and signal cutting steps as analyzeDataR.processData."""
  dataTCT = TCTData( filename )
  dataTCT.bulk = bulk
  getData( dataTCT )
  convertAndShiftData( dataTCT )

  if noiseFile:
    noiseTCT = TCTData( noiseFile )
    noiseTCT.bulk = bulk
    getData( noiseTCT )
    convertAndShiftData( noiseTCT )
    removeElectronicNoise( dataTCT, noiseTCT )
  else:
    # No noise file supplied: fall back to the pedestal-corrected data,
    # assigned the same way removeElectronicNoise would (per-wave), so
    # dataTCT.noiselessData ends up in the structure averageTheData expects.
    for wave in dataTCT.ydata:
      dataTCT.noiselessData = list( wave )

  averageTheData( dataTCT )
  cutData( dataTCT, cut = cut )
  return dataTCT


def writeCSV( outCsv, time, voltage ):
  fd = open( outCsv, "w" )
  writer = csv.writer( fd )
  writer.writerow( [ "Time(s)", "Voltage(V)" ] )
  for t, v in zip( time, voltage ):
    writer.writerow( [ t, v ] )
  fd.close()


def plotWaveform( outPng, time, voltage, title ):
  plot_parameters()
  pylab.figure( figsize = ( 8, 5 ) )
  pylab.plot( time, voltage, "k" )
  pylab.ticklabel_format( axis = 'both', style = 'sci', scilimits = ( 0, 0 ) )
  pylab.grid( True )
  pylab.xlabel( "Time(s)" )
  pylab.ylabel( "Voltage(V)" )
  pylab.title( title )
  pylab.subplots_adjust(left=0.15, right=0.95, top=0.9, bottom=0.15)
  pylab.savefig( outPng )
  pylab.close()


def parseador():
  parser = argparse.ArgumentParser( description = "Plot voltage vs. time for a single TCT bin file and export it as a CSV" )
  parser.add_argument( "-f", "--file", type = str, required = True, help = "binary data file", metavar = "" )
  parser.add_argument( "-n", "--noise_file", type = str, default = None, help = "electronic noise binary file (optional; skips noise subtraction if omitted)", metavar = "" )
  parser.add_argument( "-b", "--bulk", type = str, choices = [ "p", "n" ], default = "n", help = "bulk of the sensor. Choices = n, p. Default = %(default)s", metavar = "" )
  parser.add_argument( "-i", "--integration_window", type = str, choices = [ "signal", "peak", "whole" ], default = "signal", help = "definition of the signal cut window. Choices = signal, peak, whole. Default = %(default)s", metavar = "" )
  parser.add_argument( "-o", "--output_prefix", type = str, default = None, help = "output filename prefix (defaults to the input filename without extension)", metavar = "" )
  return parser.parse_args()


def main():
  args = parseador()
  prefix = args.output_prefix or os.path.basename( args.file ).replace( ".bin", "" )

  dataTCT = buildAverageTrace( args.file, args.noise_file, args.bulk, args.integration_window )

  # Extract only the window defined by cutData (dataTCT.initPoint : dataTCT.endPoint)
  time = np.array( dataTCT.xdata[ dataTCT.initPoint : dataTCT.endPoint ] )
  time = time - time[ 0 ]  # shift window so trace starts at t = 0
  voltage = np.array( dataTCT.averageData[ dataTCT.initPoint : dataTCT.endPoint ] )

  csvName = prefix + "_waveform.csv"
  pngName = prefix + "_waveform.png"

  writeCSV( csvName, time, voltage )
  plotWaveform( pngName, time, voltage, args.file )

  print "Wrote %s and %s" % ( pngName, csvName )


if __name__ == "__main__":
  main()