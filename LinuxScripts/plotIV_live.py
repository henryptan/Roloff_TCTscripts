#!/usr/bin/env python2
# -*- coding: utf-8 -*-
 
import pylab
import matplotlib.animation as animation
import sys
import os
 
 
def readResults( filename ):
  voltage = []
  current = []
  if not os.path.exists( filename ):
    return voltage, current
  fd = open( filename, "r" )
  lines = fd.readlines()
  fd.close()
  for line in lines:
    line = line.strip()
    if not line:
      continue
    data = line.split( "\t" )
    if len( data ) < 2:
      continue
    try:
      voltage.append( abs( float( data[ 0 ] ) ) )
      current.append( abs( float( data[ 1 ] ) ) )
    except ValueError:
      # Partial/incomplete line being written to disk - skip it, it'll be
      # complete by the next poll
      continue
  return voltage, current
 
 
def main( filename, interval_ms = 2000 ):
  fig = pylab.figure( 1, ( 7, 6 ) )
  ax = fig.add_subplot( 111 )
  label = "_".join( filename )
 
  def update( frame ):
    voltage, current = readResults( filename )
    ax.clear()
    if len( voltage ) > 0:
      ax.semilogy( voltage, current, "o-", label = label )
    ax.set_xlabel( "Absolute Voltage [V]" )
    ax.set_ylabel( "Absolute Current [A]" )
    ax.set_title( "Live IV: %s (%d points)" % ( label, len( voltage ) ) )
    ax.grid( True )
    ax.legend( loc = 0 )
    fig.tight_layout()
 
  # keep a reference so the animation isn't garbage collected
  ani = animation.FuncAnimation( fig, update, interval = interval_ms )
  pylab.show()
 
 
if __name__ == "__main__":
  if len( sys.argv ) < 2:
    print "Usage: %s <iv_datafile.txt> [poll_interval_ms]" % sys.argv[ 0 ]
    sys.exit( 1 )
  filename = sys.argv[ 1 ]
  interval_ms = int( sys.argv[ 2 ] ) if len( sys.argv ) > 2 else 2000
  main( filename, interval_ms )

