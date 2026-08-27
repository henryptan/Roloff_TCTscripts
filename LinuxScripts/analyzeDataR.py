#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from OOFlex.files.BINReader import BINReader
from TCTData import TCTData

import argparse
import numpy as np
import matplotlib
matplotlib.use( "Agg" )
import pylab
import os.path


def plot_parameters( plots = 0 ):
  """Plot format
  """
  pylab.rcParams[ 'lines.linewidth' ] = 1
  pylab.rcParams[ 'lines.markeredgewidth' ] = 1
  pylab.rcParams[ 'lines.markersize' ] = 7
  pylab.rcParams[ 'font.size' ] = 10 - plots / 2
#  pylab.rcParams[ 'font.weight' ] = 'semibold'
  pylab.rcParams[ 'axes.linewidth' ] = 2
  pylab.rcParams[ 'axes.titlesize' ] = 35 - plots / 2
  pylab.rcParams[ 'axes.labelsize' ] = 15 - plots / 2
#  pylab.rcParams[ 'axes.labelweight' ] = 'semibold'
  pylab.rcParams[ 'ytick.major.pad' ] = 9 - plots / 4
  pylab.rcParams[ 'xtick.major.pad' ] = 9 - plots / 4
  pylab.rcParams[ 'xtick.labelsize' ] = 13
  pylab.rcParams[ 'ytick.labelsize' ] = 13
  pylab.rcParams[ 'legend.fontsize' ] = 10 - plots / 1.5
  pylab.rcParams[ 'grid.linewidth' ] = 1


def getCharge( dataTCT ):
  """It calculates the charge taking into account the gain if the amplifiar from Particulars
     www.particulars.si
  """
  voltage = 8
  max_gain = 53
  rel_gain = { 6 : 0.15, 7 : 0.4, 8 : 0.6, 9 : 0.8, 10 : 0.9, 11 : 1, 12 : 1, 13 : 1, 14 : 1, 15 : 1 }
  gain = max_gain * rel_gain[ voltage ]
  charge = sum( dataTCT.cuttedData ) * dataTCT.header[ "xincr" ] / ( 50 * gain )
  return abs( charge )

def convertAndShiftData( dataTCT ):
  """Converts binary to ascii and turns positive signals from p-type
     sensors to negative. The algorithm looks for minimums, not maximums.
  """
  for wave in dataTCT.rawData:
    ywave = dataTCT.data2wave( wave )
    if dataTCT.bulk == "p":
      ywave = list( np.array( ywave ) * -1 )
    dataTCT.pedestalInit, dataTCT.pedestalEnd, pdt = pedestal( ywave )
    dataTCT.ydata = list( np.array( ywave ) - pdt )

def removeElectronicNoise( dataTCT, noiseTCT ):
  for wave in dataTCT.ydata:
    noiseless = np.array( wave ) - np.array( noiseTCT.ydata[ 0 ] )
    dataTCT.noiselessData = list( noiseless )

def averageTheData( dataTCT ):
  """It averages all the waveforms in the file.
  """
  average = np.array( len( dataTCT.noiselessData[ 0 ] ) * [ 0.0 ] )
  for wave in dataTCT.noiselessData:
    average += np.array( wave )
  average /= float( len( dataTCT.noiselessData ) )
  dataTCT.averageData = list( average )

def cutData( dataTCT, cut = "signal" ):
  """ Function that looks for the minimum in the signal and it cuts a 50ns window.
      The window has to begin 1ns before the beginning of the signal and extends
      for 50ns.
      If the argument cut is equal to peak the cut will take only the peak, not 50ns
  """
  window = [ -1e-9, 49e-9 ]
  minimum = dataTCT.averageData.index( min( dataTCT.averageData ) )
  for k in range( len( dataTCT.averageData[ : minimum + 1 ] ) - 1, -1, -1 ):
    if dataTCT.averageData[ k ] > 0.0:
      dataTCT.initSignal = k
      break
  for k in range( minimum, len( dataTCT.averageData ) ):
    if dataTCT.averageData[ k ] > 0.0:
      dataTCT.endSignal = k
      break
  dataTCT.calculateWindow( window )
  if cut == "peak":
    dataTCT.initPoint = dataTCT.initSignal
    dataTCT.endPoint = dataTCT.endSignal
  elif cut == "signal":
    dataTCT.initPoint = dataTCT.initWindow
    dataTCT.endPoint = dataTCT.endWindow
  elif cut == "whole":
    dataTCT.initPoint = 0
    dataTCT.endPoint = len( dataTCT.average)
  dataTCT.cuttedData = dataTCT.initPoint * [ 0 ] + dataTCT.averageData[ dataTCT.initPoint : dataTCT.endPoint ] + ( len( dataTCT.averageData ) - dataTCT.endPoint ) * [ 0 ]

def pedestal( data ):
  """It calculates the pedestal to eliminate any possible DC in the measure.
  """
  minimum = data.index( min( data ) )
  if minimum / 2 < 3000:
    initPoint = minimum + 2000
    endPoint = minimum + 5000
  else :
    initPoint = 0
    endPoint = minimum / 2
  pedestal = sum( data[ initPoint : endPoint ] ) / float( endPoint - initPoint )
  return initPoint, endPoint, pedestal

def plotAnalysis( dataTCT ):
  """Plot the different steps I make to the waveforms to get the signal and
     integrate it and calculate the charge later. These plots is my check to
     know I am doing the things right.
  """
  plot_parameters()
  fig = pylab.figure( 1, ( 8, 7 ) )
  fig.add_subplot( 221 )
  pylab.plot( dataTCT.xdata, dataTCT.ydata[ 0 ], "k", label = "Raw data" )
  #ftemp = open( dataTCT.filename.replace( ".bin", ".txt" ), "w" )
  #for i in range(len(dataTCT.xdata)):
  #    ftemp.write( str(dataTCT.xdata[i]) + "\t" + str(dataTCT.noiselessData[ 0 ][ i ]) + "\n" )
  #ftemp.close()
  pylab.plot( dataTCT.xdata, dataTCT.noiselessData[ 0 ], "b", label = "Noiseless data" )
  pylab.ticklabel_format( axis = 'both', style = 'sci', scilimits = ( 0, 0 ) )
  pylab.legend( loc = 0 )
  pylab.grid( True )
  pylab.xlabel( "Time(s)" )
  pylab.ylabel( "Voltage(V)" )
  fig.add_subplot( 222 )
  pylab.plot( dataTCT.xdata[ dataTCT.pedestalInit : dataTCT.pedestalEnd ], dataTCT.ydata[ 0 ][ dataTCT.pedestalInit : dataTCT.pedestalEnd ], "k", label = "Pedestal Example" )
  pylab.ticklabel_format( axis = 'both', style = 'sci', scilimits = ( 0, 0 ) )
  pylab.legend( loc = 0 )
  pylab.grid( True )
  pylab.xlabel( "Time(s)" )
  pylab.ylabel( "Voltage(V)" )
  fig.add_subplot( 223 )
  pylab.plot( dataTCT.xdata[ dataTCT.initPoint : dataTCT.endPoint ], dataTCT.averageData[ dataTCT.initPoint : dataTCT.endPoint ], "k", label = "50ns window" )
  pylab.ticklabel_format( axis = 'both', style = 'sci', scilimits = ( 0, 0 ) )
  pylab.legend( loc = 0 )
  pylab.grid( True )
  pylab.legend( loc = 0 )
  pylab.xlabel( "Time(s)" )
  pylab.ylabel( "Voltage(V)" )
  fig.add_subplot( 224 )
  pylab.plot( dataTCT.xdata[ dataTCT.initPoint - 100 : dataTCT.endPoint + 100  ], dataTCT.cuttedData[ dataTCT.initPoint - 100 : dataTCT.endPoint + 100 ], "k", label = "Integrating\nwindow" )
  pylab.ticklabel_format( axis = 'both', style = 'sci', scilimits = ( 0, 0 ) )
  pylab.legend( loc = 0 )
  pylab.grid( True )
  pylab.xlabel( "Time(s)" )
  pylab.ylabel( "Voltage(V) " )
  pylab.tight_layout()
  pylab.savefig( dataTCT.filename.replace( ".bin", ".png" ) )
  pylab.close()

def processData( dataTCT, noiseTCT, verbosity, cut = "signal" ):
  """Different steps to finally get the charge from the waveforms
  """
  convertAndShiftData( dataTCT )
  removeElectronicNoise( dataTCT, noiseTCT )
  averageTheData( dataTCT )
  cutData( dataTCT, cut )
  charge = getCharge( dataTCT )
  if verbosity:
    plotAnalysis( dataTCT )
  return charge

def natSorting( results ):
  """Natural sorting to save the data in the results file
  """
  indexes = {}
  sorted_data = []
  for line in results:
    indexes[ int( line.split( "\t" )[ 0 ] ) ] = line
  for key in sorted( indexes.keys() )[ : : -1 ]:
    sorted_data.append( indexes[ key ] )
  return sorted_data

def parseador():
  parser = argparse.ArgumentParser( description = "TCT analysis" )
  parser.add_argument( "-f", "--files", type = str, nargs = "+", help = "binary data files" )
  parser.add_argument( "-n", "--noise_file", type = str, help = "electronic noise file" )
  parser.add_argument( "-b", "--bulk", type = str, choices = [ "p", "n" ], default = "n", help = "bulk of the sensor. Choices = n, p. Default = %(default)s", metavar = "" )
  parser.add_argument( "-i", "--integration_window", type = str, choices = [ "signal", "peak", "whole" ], default = "signal", help = "definiton of the integration window, 50ns since the beginning of the peak or only the peak. Choices = signal, peak. Default = %(default)s", metavar = "" )
  parser.add_argument( "-v", "--verbosity", type = int, required = False, default = 1, help = "Verbosity, plots for individual scans are produced only when the verbosity is on. Choices = 0, 1", metavar = "" )
  args = parser.parse_args()
  return args

def getData( dataTCT ):
  """Binary reader and converter to ascii data.
  """
  binreader = BINReader( dataTCT.filename )
  binreader.readData()
  dataTCT.header = binreader.header
  dataTCT.rawData = binreader.data
  binreader.close()

def strmResults( charge ):
  """Plot the results in the screen to monitor while
     the program is running.
  """
  #print "Charge: %eC" % charge
  pairs = charge / ( 1.602176e-19 * 2 )
  #print "Pairs: %d" % pairs
  mips = charge / ( 1.602176e-19 * 2 * 80 * 300 )
  #print "MIPS(300um): %.2f" % mips
  return pairs, mips

def writeResults( filename, header, results ):
  """Function to write the results in a txt file.
  """
  if os.path.isfile( filename ):
    fd = open( filename, "a" )
  else:
    fd = open( filename, "w" )
    fd.write( header )
  fd.writelines( results )
  fd.close()

def main( files, noiseFile, bulk, integrationWindow, verbosity ):
  results = []
  dataTCT = []
  noiseTCT = TCTData( noiseFile )
  noiseTCT.bulk = bulk
  getData( noiseTCT )
  convertAndShiftData( noiseTCT )
  count = 0
  for filename in files:
    dataTCT.append( TCTData( filename ) )
    dataTCT[ -1 ].bulk = bulk
    voltage = [ value for value in dataTCT[ -1 ].filename.split( "_" ) if value[ 0 ] == "V" and value[ -1 ] == "V" ][ 0 ].replace( "V", "" )
    getData( dataTCT[ -1 ] )
    charge = processData( dataTCT[ -1 ], noiseTCT, verbosity )
    pairs, mips = strmResults( charge )
    if (verbosity or count % 100 == 0):
      print "File: %s" % dataTCT[ -1 ].filename
      print "Charge: %eC" % charge
      print "Pairs: %d" % pairs
      print "MIPS(300um): %.2f" % mips
    results.append( voltage + "\t" + str( charge ) + "\t" + str( pairs ) + "\t" + str( mips ) + "\n" )
    count = count + 1
  results = natSorting( results )
  writeResults( "results.txt", "Voltage(V)\tCharge(C)\tPairs\tMIPS\n", results )


if __name__ == "__main__":
  args = parseador()
  main( args.files, args.noise_file, args.bulk, args.integration_window, args.verbosity )
