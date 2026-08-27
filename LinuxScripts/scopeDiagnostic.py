#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Standalone diagnostic: reads a single waveform from the LeCroy WavePro 725Zi
over VXI-11 and plots it. Independent of focusR -- no laser motion, no
averaging, no BINWriter. Use this to test the scope link/read chain on a
signal known to be present (e.g. the laser trigger on C2), separate from
any network troubleshooting.

Usage:
  python2 scopeDiagnostic.py [channel]

  channel defaults to "C2" if not given.
"""
import sys
import struct
import matplotlib
matplotlib.use( "Agg" )
import pylab

# If these imports fail with ImportError, uncomment the next two lines and
# set the path to wherever the OOHw package's parent directory lives:
# sys.path.append( "/home/trenado/Desktop/HwCont" )

from OOHw.interface.VXI11Interface import VXI11Interface
from OOHw.instruments.Lecroy.scopes.Lc725Zi import Lc725Zi

SCOPE_IP   = "10.38.89.147"
OUTPUT_PNG = "channel_diagnostic.png"


def main():
  channel = sys.argv[ 1 ] if len( sys.argv ) > 1 else "C2"

  print "Connecting to scope at %s ..." % SCOPE_IP
  interface = VXI11Interface( SCOPE_IP, 0 )
  scope = Lc725Zi( interface )

  print "Clearing status/event queues (*CLS) ..."
  scope.write( "*CLS" )

  print "Reading waveform from %s ..." % channel
  rawData, nrPoints, bytesPerPoint = scope.readWaveformBIN( channel )
  preamble = scope.preamble

  print "Got %d points, %d bytes/point" % ( nrPoints, bytesPerPoint )
  print "xincr=%s xzero=%s ymult=%s yzero=%s" % (
    preamble[ "xincr" ], preamble[ "xzero" ], preamble[ "ymult" ], preamble[ "yzero" ]
  )

  fmt = { 1 : "b", 2 : "h" }[ bytesPerPoint ]
  raw = struct.unpack( "<%d%s" % ( nrPoints, fmt ), rawData[ : nrPoints * bytesPerPoint ] )

  voltage = [ preamble[ "ymult" ] * value + preamble[ "yzero" ] for value in raw ]
  time    = [ preamble[ "xzero" ] + i * preamble[ "xincr" ] for i in range( nrPoints ) ]

  pylab.figure( 1, ( 9, 5 ) )
  pylab.plot( time, voltage, "b-", linewidth = 0.8 )
  pylab.xlabel( "Time (s)" )
  pylab.ylabel( "Voltage (V)" )
  pylab.title( "%s waveform" % channel )
  pylab.grid( True )
  pylab.tight_layout()
  pylab.savefig( OUTPUT_PNG )
  pylab.close()

  print "Saved plot to %s" % OUTPUT_PNG


if __name__ == "__main__":
  main()
