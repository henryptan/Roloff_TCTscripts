#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import argparse
import shutil
from OOHw.interface.InterfaceFactory import InterfaceFactory
from OOHw.files.BINWriter import BINWriter
import powerSupply as pW
import coordinatesFile as cF
import stages
import time

def confScope( scope, channels ):
  for channel in channels:
    c_name = "C" + str( channel )
    f_name = "F" + str( channel )
    scope.coupling( c_name, "D50" )
    scope.trace( c_name, "ON" )
    scope.trace( f_name, "ON" )

def acquireData( scope, numAcquisitions, averageNumber, filename, channel ):
  binwriter = BINWriter( filename )
  target = int( averageNumber )
  for i in range( 1, numAcquisitions + 1 ):
    scope.clearSweeps()
    current = int( scope.obtainPreamble( channel )[ "SWEEPS_PER_ACQ" ] )
    while current < target:
      print "Sweeps: %d/%d" % ( current, target )
      time.sleep( .5 )
      current = int( scope.obtainPreamble( channel )[ "SWEEPS_PER_ACQ" ] )
    waveform, points, bytesPoint = scope.readWaveformBIN( channel )
    if i == 1:
      binwriter.header = scope.preamble
      binwriter.bytesPerPoint( bytesPoint )
      binwriter.pointsPerMeasurement( points )
    binwriter.addData( waveform )
  binwriter.writeData()
  binwriter.close()

def getElectronicNoiseSignal( s, sensors, args, scope, channels ):
  coord = list( sensors[ args.subparser ] )
  coord[ 1 ] += 5000
  stages.sendtoCoordinates( s, coord )
  print "\nAcquiring electronic noise for channels:", args.channel
  for ch, target_ch in zip( args.channel, channels ):
    filename = "electronicNoise_ch%s.bin" % ch
    acquireData( scope, 1, args.average_number, filename, target_ch )
  stages.sendtoCoordinates( s, sensors[ args.subparser ] )

def findOptimumPosition( sensors, scope, args, target_channels ):
  axes = [ "x", "y", "z" ]
  if args.size in [ "Ref", "Small" ]:
    rangesteps = { "x" : [ -2000, 2000, 500 ], "y" : [ -2000, 2000, 500 ], "z" : [ -1000, 1500, 100 ] }
  elif args.size in [ "Rough" ]:
    rangesteps = { "x" : [ -1500, 1500, 150 ], "y" : [ -1500, 1500, 150 ], "z" : [ -9000, 15000, 100 ] }
  elif args.size in [ "Medium" ]:
    rangesteps = { "x" : [ -750, 750, 75 ], "y" : [ -750, 750, 75 ], "z" : [ -9000, 15000, 100 ] }
  elif args.size in [ "Fine" ]:
    rangesteps = { "x" : [ -100, 100, 10 ], "y" : [ -100, 100, 10 ], "z" : [ -9000, 15000, 100 ] }
  else:
    rangesteps = { "x" : [ -2500, 2500, 250 ], "y" : [ -2500, 2500, 250 ], "z" : [ -13000, 4000, 300 ] }

  center = sensors[ args.subparser ]
  rangoX = range( rangesteps[ "x" ][ 0 ], rangesteps[ "x" ][ 1 ], rangesteps[ "x" ][ 2 ] )
  rangoY = range( rangesteps[ "y" ][ 0 ], rangesteps[ "y" ][ 1 ], rangesteps[ "y" ][ 2 ] )
  s = stages.open_socket()

  for i in rangoX:
    for j in rangoY:
      coordinates = center[ : ]
      coordinates[ 0 ] += i
      coordinates[ 1 ] += j
      print "\nAcquiring in (x,y): (%d/%d, %d/%d)" % ( rangoX.index( i ) + 1, len( rangoX ), rangoY.index( j ) + 1, len( rangoY ) )
      cc = stages.sendtoCoordinates( s, coordinates )
      if cc == [ "out", "out", "out" ]:
        stages.close_socket( s )
        return cc
      
      for ch, target_ch in zip( args.channel, target_channels ):
        filename = "scan2D_%s_ch%s_x%s_y%s.bin" % (
          args.subparser,
          str( ch ),
          str( center[ axes.index( "x" ) ] + i ),
          str( center[ axes.index( "y" ) ] + j )
        )
        acquireData( scope, args.acquisition_number, args.average_number, filename, target_ch )

  stages.close_socket( s )

def parseador():
  parser = argparse.ArgumentParser( description = "Laser Focus program" )
  subparser = parser.add_subparsers()
  for p in [ "First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Ref" ]:
    sp = subparser.add_parser( p, help = "Focus on the %s diode" % p )
    sp.set_defaults( subparser = p )

  parser.add_argument( "-f", "--files", nargs="+", help = "list of files to analyze", metavar = "" )
  parser.add_argument( "-a", "--acquisition_mode", type = str, choices = [ "sample", "peakdetect", "average", "envelope" ], default = "sample", help = "acquisition mode", metavar = "" )
  parser.add_argument( "-g", "--average_number", type = str, default = "100", help = "average number", metavar = "" )
  parser.add_argument( "-n", "--acquisition_number", type = int, default = 100, help = "number of acquisitions", metavar = "" )
  parser.add_argument( "-c", "--channel", nargs="+", type = int, default = [1], help = "acquisition channels list (e.g., -c 1 2)", metavar = "" )
  parser.add_argument( "-v", "--voltage", type = str, default = "0", help = "bias voltage", metavar = ""  )
  parser.add_argument( "-m", "--compliance", type = float, default = "10e-6", help = "compliance", metavar = "" )
  parser.add_argument( "-l", "--amp_voltage", type = str, default = "8", help = "amp voltage", metavar = ""  )
  parser.add_argument( "-j", "--amp_compliance", type = float, default = "300e-3", help = "amp compliance", metavar = "" )
  parser.add_argument( "-t", "--temperature", type = str, default = "32", help = "temperature", metavar = ""  )
  parser.add_argument( "-e", "--axis", type = list, default = "xyz", help = "focus axis", metavar = "" )
  parser.add_argument( "-s", "--size", type = str, default = "Ref", choices = [ "Small", "Big", "Ref", "Rough", "Medium", "Fine" ], help = "grid size", metavar = ""  )
  parser.add_argument( "-b", "--bulk", type = str, choices = [ "p", "n" ], help = "bulk of sensor", metavar = "" )
  parser.add_argument( "-x", "--no_turn_off", action='store_true', help = "do not turn off HV" )
  parser.add_argument( "-y", "--no_turn_on", action='store_true', help = "do not control HV" )
  
  args = parser.parse_args()
  if args.acquisition_mode == "average":
    args.acquisition_number = 1
  return args

def main( args ):
  factory = InterfaceFactory( "setupBrown.ini" )
  scope = factory.getDevice( "scope" )
  keithley = factory.getDevice( "highVoltage" )
  shutil.copyfile( "sensors.txt", "sensors_back.txt" )

  if not args.no_turn_on:
    pW.setPowerSupply( keithley, args.voltage, args.compliance )

  confScope( scope, args.channel )

  target_channels = []
  for ch in args.channel:
    if args.acquisition_mode == "average":
      scope.average( args.average_number )
      scope.controlAcquisition( "NORMAL" )
      target_channels.append( "F" + str( ch ) )
    else:
      scope.controlAcquisition( "SINGLE" )
      target_channels.append( "C" + str( ch ) )

  sensors = cF.getCoordFromFile()
  s = stages.open_socket()
  stages.sendtoCoordinates( s, sensors[ args.subparser ] )
  getElectronicNoiseSignal( s, sensors, args, scope, target_channels )
  stages.close_socket( s )
  findOptimumPosition( sensors, scope, args, target_channels )
  
  if not args.no_turn_off:
    pW.turnOFFPowerSupply( keithley )

if __name__ == "__main__":
  args = parseador()
  main( args )
