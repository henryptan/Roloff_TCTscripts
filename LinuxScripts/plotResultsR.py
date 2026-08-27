#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import sys
import matplotlib
matplotlib.use( "Agg" )
import pylab
import analyzeData as aD

def plot( voltage, charge, pairs, mips):
  aD.plot_parameters()
  fig = pylab.figure( 1, ( 7, 6 ) )
  fig.add_subplot( 111 )
  pylab.plot( voltage, pairs, "ko", fillstyle = "none" )
  pylab.ticklabel_format( axis = 'y', style = 'sci', scilimits = ( 0, 0 ) )
  pylab.xlabel( "Voltage (V)" )
  pylab.ylabel( "Pairs" )
  pylab.grid( True )
  pylab.tight_layout()
  pylab.savefig( "results.png" )
  pylab.close()

def readResults( filename ):
  voltage = []
  charge = []
  pairs = []
  mips = []
  fd = open( filename, "r" )
  lines = fd.readlines()
  fd.close()
  for i in range( 1, len( lines ) ):
    line = lines[ i ].replace( "\n", "" ).split( "\t" )
    voltage.append( int( line[ 0 ] ) )
    charge.append( float( line[ 1 ] ) )
    pairs.append( float( line[ 2 ] ) )
    mips.append( float( line[ 3 ] ) )
  return voltage, charge, pairs, mips

def main( filename ):
  voltage, charge, pairs, mips = readResults( filename )
  plot( voltage, charge, pairs, mips )


if __name__ == "__main__":
 main( sys.argv[ -1 ] )
