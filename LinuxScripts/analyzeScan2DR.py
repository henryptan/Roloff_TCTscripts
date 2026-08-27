#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import argparse
import analyzeData as aD
from TCTData import TCTData
import coordinatesFile as cF
import shutil

def processAndAnalysis( filename, ch, count, args, cut = "signal" ):
  noiseFile = "electronicNoise_ch%s.bin" % ch
  if not os.path.exists( noiseFile ):
    noiseFile = "electronicNoise.bin"
  noiseTCT = TCTData( noiseFile )
  noiseTCT.bulk = args.bulk
  dataTCT = TCTData( filename )
  dataTCT.bulk = args.bulk
  aD.getData( noiseTCT )
  aD.getData( dataTCT )
  aD.convertAndShiftData( noiseTCT )
  charge = aD.processData( dataTCT, noiseTCT, args.verbosity, cut )
  pairs, mips = aD.strmResults( charge )
  if (args.verbosity or count % 100 == 0):
    print "File: %s | Charge: %eC | Pairs: %d | MIPs: %.2f" % ( filename, charge, pairs, mips )
  return pairs

def readResults():
  channels, pairs, x, y, data_files = [], [], [], [], []
  if not os.path.exists( "scan2D.txt" ):
    return data_files, channels, x, y, pairs
  fd = open( "scan2D.txt", "r" )
  lines = fd.readlines()
  for i in range( 1, len( lines ) ):
    line = lines[ i ].replace( "\n", "" ).split( "\t" )
    data_files.append( line[ 0 ] )
    channels.append( int( line[ 1 ] ) )
    x.append( int( line[ 2 ] ) )
    y.append( int( line[ 3 ] ) )
    pairs.append( float( line[ 4 ] ) )
  fd.close()
  return data_files, channels, x, y, pairs

def writeResults( data_files, channels, x, y, pairs ):
  fd = open( "scan2D.txt", "w" )
  fd.write( "File\tChannel\tx(um)\ty(um)\tPairs\n" )
  for i in range( len( pairs ) ):
    fd.write( "%s\t%d\t%d\t%d\t%f\n" % ( data_files[ i ], channels[ i ], x[ i ], y[ i ], pairs[ i ] ) )
  fd.close()

def parseFilename( filename ):
  tokens = filename.replace( ".bin", "" ).split( "_" )
  ch = 1
  x_val, y_val = 0, 0
  for t in tokens:
    if t.startswith( "ch" ):
      ch = int( t[ 2: ] )
    elif t.startswith( "x" ):
      x_val = int( t[ 1: ] )
    elif t.startswith( "y" ):
      y_val = int( t[ 1: ] )
  return ch, x_val, y_val

def natSorting( dataFiles ):
  data = {}
  files = []
  for filename in dataFiles:
    ch, x, y = parseFilename( filename )
    if ch not in data:
      data[ ch ] = {}
    if x not in data[ ch ]:
      data[ ch ][ x ] = {}
    data[ ch ][ x ][ y ] = filename
  for ch in sorted( data.keys() ):
    for x in sorted( data[ ch ].keys() ):
      for y in sorted( data[ ch ][ x ].keys() ):
        files.append( data[ ch ][ x ][ y ] )
  return files

def loadChannelMap( path = "channel_map.txt" ):
  """Read a channel -> sensor name mapping written by runScan2D_R.sh
  (one 'channel:sensor' pair per line). Returns {} if the file is absent."""
  mapping = {}
  if os.path.exists( path ):
    fd = open( path, "r" )
    for line in fd.readlines():
      line = line.strip()
      if not line or ":" not in line:
        continue
      ch_str, sensor_name = line.split( ":", 1 )
      try:
        mapping[ int( ch_str ) ] = sensor_name.strip()
      except ValueError:
        continue
    fd.close()
  return mapping

def parseChannelMap( channel_map_args ):
  """Parse '-c 1:First 2:Second' style CLI entries into {1: 'First', 2: 'Second'}."""
  mapping = {}
  if channel_map_args:
    for item in channel_map_args:
      ch_str, sensor_name = item.split( ":", 1 )
      mapping[ int( ch_str ) ] = sensor_name
  return mapping

def alignChannel( ch, channels, x, y, pairs, data_files, channel_map, sensors ):
  """Find the optimum (x,y) for a single channel and update the coordinates
  of the sensor that channel corresponds to. Returns the (possibly updated)
  sensors dict and the sensor name that was aligned (None if channel absent)."""
  ch_indices = [ i for i, c in enumerate( channels ) if c == ch ]
  if not ch_indices:
    return sensors, None

  max_idx = max( ch_indices, key = lambda i: pairs[ i ] )
  maxx, maxy = x[ max_idx ], y[ max_idx ]

  if ch in channel_map:
    sensor = channel_map[ ch ]
  else:
    # Fall back to the scan's center/reference sensor encoded in the filename
    # (this matches the original single-channel behaviour).
    sensor = data_files[ max_idx ].split( "_" )[ 1 ]

  newCoord = sensors[ sensor ]
  newCoord[ 0 ], newCoord[ 1 ] = maxx, maxy
  X, Y, Z = newCoord
  if sensor == "Ref":
    cF.changeRelCoordRefDiode( X, Y, Z )
  else:
    sensors = cF.changeCoordinate( sensors, sensor, X, Y, Z )
    sensors = cF.setCoordHoldSyst( sensors )
  print "New Coord, channel %d, sensor %s: %s %s %s" % ( ch, sensor, X, Y, Z )
  return sensors, sensor

def parseador():
  parser = argparse.ArgumentParser( description = "Scan2D analyzer" )
  parser.add_argument( "-b", "--bulk", type = str, required = True, choices = [ "p", "n" ], help = "bulk of the sensor", metavar = "" )
  parser.add_argument( "-v", "--verbosity", type = int, required = False, default = 1, help = "Verbosity", metavar = "" )
  parser.add_argument( "-c", "--channel_map", nargs = "+", type = str, default = None, help = "channel:sensor pairs, e.g. -c 1:First 2:Second (defaults to channel_map.txt if present)", metavar = "" )
  return parser.parse_args()

def main( args ):
  data_files, channels, x, y, pairs = readResults()
  bin_files = [ fd for fd in os.listdir( "." ) if "scan2D" in fd and ".bin" in fd ]
  nTotFiles = len( bin_files )
  count = 0

  for filename in natSorting( bin_files ):
    if filename not in data_files:
      ch, x_val, y_val = parseFilename( filename )
      data_files.append( filename )
      channels.append( ch )
      x.append( x_val )
      y.append( y_val )
      pairs.append( processAndAnalysis( filename, ch, count, args ) )
      count += 1

  writeResults( data_files, channels, x, y, pairs )

  # Align coordinates for EVERY channel present in the data, so a single
  # multi-channel scan (multiple sensors scanned simultaneously) updates
  # each sensor's own position rather than only channel 1's.
  channel_map = parseChannelMap( args.channel_map )
  if not channel_map:
    channel_map = loadChannelMap()  # falls back to channel_map.txt, {} if absent

  shutil.copyfile( "sensors.txt", "sensors_back.txt" )
  sensors = cF.getCoordFromFile()

  updated_any = False
  for ch in sorted( set( channels ) ):
    sensors, sensor = alignChannel( ch, channels, x, y, pairs, data_files, channel_map, sensors )
    if sensor is not None and sensor != "Ref":
      updated_any = True

  if updated_any:
    cF.writeCoord2File( sensors )

if __name__ == "__main__":
  args = parseador()
  main( args )