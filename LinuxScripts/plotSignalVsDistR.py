#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import argparse
import matplotlib
matplotlib.use( "Agg" )
import pylab

ORDER = [ "First", "Second", "Third", "Fourth" ]


def readResults( filename, sensors = None, bias = None ):
  """Reads the results file written by TCTposR.py.
     Returns { sensor : ( [ distances ], [ charges ] ) }
  """
  data = {}
  with open( filename ) as fd:
    lines = fd.readlines()
  for line in lines[ 1 : ]:
    fields = line.rstrip( "\n" ).split( "\t" )
    if len( fields ) < 9:
      continue
    sensor = fields[ 0 ]
    if sensors and sensor not in sensors:
      continue
    if bias is not None and float( fields[ 2 ] ) != bias:
      continue
    distances, charges = data.setdefault( sensor, ( [], [] ) )
    distances.append( float( fields[ 7 ] ) )
    charges.append( float( fields[ 8 ] ) )
  return data

def plotSensor( sensor, distances, charges, output, unit ):
  fig = pylab.figure( 1, ( 7, 5 ) )
  pylab.plot( distances, charges, "ko" )
  pylab.ticklabel_format( axis = "y", style = "sci", scilimits = ( 0, 0 ) )
  pylab.title( "%s sensor" % sensor )
  pylab.xlabel( "Distance laser - sensor (%s)" % unit )
  pylab.ylabel( "Signal: charge (C)" )
  pylab.grid( True )
  pylab.tight_layout()
  pylab.savefig( output )
  pylab.close()

def parseador():
  parser = argparse.ArgumentParser( description = "Signal vs distance plots (one per sensor) from the TCTposR results file" )
  parser.add_argument( "-f", "--file", type = str, default = "positionScan_results.txt", help = "results file. Default = %(default)s", metavar = "" )
  parser.add_argument( "-o", "--output", type = str, default = "signal_vs_distance", help = "output name prefix; the sensor name and .png are added. Default = %(default)s", metavar = "" )
  parser.add_argument( "-s", "--sensors", type = str, nargs = "+", help = "only plot these sensors (First Second Third Fourth)", metavar = "" )
  parser.add_argument( "-v", "--voltage", type = float, help = "only plot this bias voltage", metavar = "" )
  parser.add_argument( "-u", "--unit", type = str, default = "um", help = "distance unit for the axis label. Default = %(default)s", metavar = "" )
  return parser.parse_args()

def main():
  args = parseador()
  sensors = [ s.capitalize() for s in args.sensors ] if args.sensors else None
  data = readResults( args.file, sensors, args.voltage )
  if not data:
    print "No data found in %s with the given filters" % args.file
    return
  for sensor in sorted( data.keys(), key = lambda s: ORDER.index( s ) if s in ORDER else len( ORDER ) ):
    distances, charges = data[ sensor ]
    output = "%s_%s.png" % ( args.output, sensor )
    plotSensor( sensor, distances, charges, output, args.unit )
    print "Saved %s" % output


if __name__ == "__main__":
  main()
