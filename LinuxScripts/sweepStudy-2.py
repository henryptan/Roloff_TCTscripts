#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""Sweep-number study.

Takes N_MEASUREMENTS raw (un-averaged) sweeps at the CURRENT stage position
(position must be set up before running), at a fixed bias voltage, and stores
them in a single .bin file. Then, for each requested averaging number
(1, 5, 10, ..., 500) it averages the first N sweeps, runs the same analysis
as analyzeData.py (pedestal removal, electronic-noise subtraction, negative-lobe
integration, conversion to charge) and plots charge vs. number of sweeps.

Why raw sweeps instead of the scope's own averaging?
  Averaging the first N raw sweeps in software is equivalent to what the scope
  does with F-trace averaging at N sweeps, but lets us get every N from ONE
  acquisition of 500 sweeps instead of 12 separate ones.

Besides the "first N sweeps" curve you asked for, the script also splits the
500 sweeps into non-overlapping groups of N (e.g. ten groups of 50) and
computes the charge for each group. That shows the spread you can expect at
each N, which is what actually tells you when the value has stopped changing.

Usage (acquire + analyze):
  ./sweepStudy.py -b n -c 1
Re-analyze an existing file without touching the hardware:
  ./sweepStudy.py -b n -c 1 -f sweepStudy_ch1_V-100.bin

Place this file in the same directory as scan2DR.py / analyzeData.py.
"""

from __future__ import print_function

import argparse
import os
import time

import numpy as np
import matplotlib
matplotlib.use( "Agg" )
import pylab

import analyzeData as aD
from TCTData import TCTData

DEFAULT_COUNTS = [ 1, 5, 10, 20, 30, 40, 50, 100, 200, 300, 400, 500 ]


# ----------------------------------------------------------------------------
# Acquisition
# ----------------------------------------------------------------------------
def acquireRaw( scope, n, filename, channel, mode, delay, timeout ):
  """Acquire n raw sweeps from `channel` into filename, guaranteeing that each
  stored waveform is a NEW acquisition (not a re-read of the previous one).
  mode = "single": re-arm the scope (SINGLE) before every sweep.
  mode = "normal": scope free-runs; we wait for a fresh trigger between reads.
  Each read is repeated until the waveform differs from the previous one."""
  from OOHw.files.BINWriter import BINWriter
  writer = BINWriter( filename )
  previous = None
  for i in range( 1, n + 1 ):
    if mode == "single":
      scope.controlAcquisition( "SINGLE" )  # re-arm for one new sweep
    scope.clearSweeps()
    t0 = time.time()
    while True:
      time.sleep( delay )
      waveform, points, bytesPoint = scope.readWaveformBIN( channel )
      if previous is None or not np.array_equal( np.asarray( waveform ), np.asarray( previous ) ):
        break
      if time.time() - t0 > timeout:
        raise RuntimeError( "Sweep %d: scope kept returning the same waveform for %d s. "
                            "It is not acquiring new sweeps." % ( i, timeout ) )
    previous = waveform
    if i == 1:
      writer.header = scope.preamble
      writer.bytesPerPoint( bytesPoint )
      writer.pointsPerMeasurement( points )
    writer.addData( waveform )
    if i % 10 == 0 or i == n:
      print( "Sweep %d/%d" % ( i, n ) )
  writer.writeData()
  writer.close()


def acquire( args, filename ):
  """Take args.num_measurements raw sweeps on one channel and save to filename.
  Reuses confScope/acquireData from scan2DR.py so the acquisition is identical
  to what the scans do. Hardware modules are imported here so that the analysis
  part can run on a machine without the instruments."""
  from OOHw.interface.InterfaceFactory import InterfaceFactory
  import powerSupply as pW
  from scan2DR import confScope

  factory = InterfaceFactory( "setupBrown.ini" )
  scope = factory.getDevice( "scope" )
  keithley = factory.getDevice( "highVoltage" )

  if not args.no_turn_on:
    pW.setPowerSupply( keithley, args.voltage, args.compliance )
  try:
    confScope( scope, [ args.channel ] )
    if args.mode == "normal":
      scope.controlAcquisition( "NORMAL" )
    print( "Acquiring %d raw sweeps on channel %d at %s V (%s mode)..." % (
      args.num_measurements, args.channel, args.voltage, args.mode ) )
    acquireRaw( scope, args.num_measurements, filename, "C%d" % args.channel,
                args.mode, args.delay, args.timeout )
  finally:
    if not args.no_turn_off:
      pW.turnOFFPowerSupply( keithley )


# ----------------------------------------------------------------------------
# Analysis
# ----------------------------------------------------------------------------
class _Wave( object ):
  """Minimal stand-in for TCTData so we can reuse aD.cutData / aD.getCharge
  on an already averaged waveform."""
  pass


def loadWaves( filename, bulk ):
  """Read a .bin file and return ( array[nWaves, nPoints] in volts, header ).
  p-type signals are flipped so the algorithm always looks for a minimum."""
  tct = TCTData( filename )
  tct.bulk = bulk
  aD.getData( tct )
  waves = []
  for raw in tct.rawData:
    w = np.array( tct.data2wave( raw ), dtype = float )
    if bulk == "p":
      w = -w
    waves.append( w )
  return np.array( waves ), tct.header


def loadNoise( path, bulk ):
  """Electronic noise waveform, processed like in analyzeData.convertAndShiftData
  (pedestal removed). Returns None if no file is available."""
  if path is None or not os.path.exists( path ):
    return None
  waves, _ = loadWaves( path, bulk )
  avg = waves.mean( axis = 0 )
  _, _, pdt = aD.pedestal( list( avg ) )
  return avg - pdt


def chargeOfAverage( avg, header, noise ):
  """Same chain as analyzeData.processData for one (already averaged) waveform:
  pedestal -> subtract electronic noise -> negative-lobe window -> charge."""
  _, _, pdt = aD.pedestal( list( avg ) )
  y = avg - pdt
  if noise is not None:
    y = y - noise
  wave = _Wave()
  wave.averageData = list( y )
  wave.header = header
  wave.calculateWindow = lambda window: None  # only needed for plotting windows
  aD.cutData( wave, "peak" )
  return aD.getCharge( wave )


def analyze( waves, header, noise, counts ):
  """For every N in counts, compute the charge of the average of the first N
  sweeps and of every non-overlapping block of N sweeps."""
  total = len( waves )
  rows = []
  for n in counts:
    nblocks = total // n
    block_charges = []
    for b in range( nblocks ):
      avg = waves[ b * n : ( b + 1 ) * n ].mean( axis = 0 )
      block_charges.append( chargeOfAverage( avg, header, noise ) )
    block_charges = np.array( block_charges )
    first = block_charges[ 0 ]  # block 0 == first N sweeps
    pairs, mips = aD.strmResults( first )
    std = block_charges.std( ddof = 1 ) if nblocks > 1 else float( "nan" )
    rows.append( { "n" : n, "charge" : first, "pairs" : pairs, "mips" : mips,
                   "blocks" : block_charges, "mean" : block_charges.mean(), "std" : std } )
    print( "N = %4d | charge(first N) = %.4e C | pairs = %d | blocks = %d | block std = %.2e C" % (
      n, first, pairs, nblocks, std ) )
  return rows


def settlingPoint( rows, tolerance ):
  """Smallest N from which the first-N charge stays within `tolerance` percent
  of the value at the largest N."""
  final = rows[ -1 ][ "charge" ]
  for i in range( len( rows ) ):
    if all( abs( r[ "charge" ] - final ) / final * 100.0 <= tolerance for r in rows[ i : ] ):
      return rows[ i ][ "n" ]
  return rows[ -1 ][ "n" ]


def writeTable( rows, filename ):
  fd = open( filename, "w" )
  fd.write( "N\tCharge_firstN(C)\tPairs\tMIPs\tBlocks\tBlockMean(C)\tBlockStd(C)\n" )
  for r in rows:
    fd.write( "%d\t%e\t%f\t%f\t%d\t%e\t%e\n" % (
      r[ "n" ], r[ "charge" ], r[ "pairs" ], r[ "mips" ], len( r[ "blocks" ] ), r[ "mean" ], r[ "std" ] ) )
  fd.close()


def plot( rows, tolerance, settle, filename, title ):
  counts = [ r[ "n" ] for r in rows ]
  charges = np.array( [ r[ "charge" ] for r in rows ] )
  final = charges[ -1 ]

  fig = pylab.figure( 1, ( 9, 9 ) )

  ax1 = fig.add_subplot( 211 )
  # every non-overlapping block, to show the scatter at each N
  for r in rows:
    pylab.plot( [ r[ "n" ] ] * len( r[ "blocks" ] ), r[ "blocks" ], ".", color = "0.65", markersize = 4 )
  pylab.plot( [], [], ".", color = "0.65", label = "Independent groups of N sweeps" )
  pylab.plot( counts, charges, "o-", color = "b", label = "Average of first N sweeps" )
  pylab.axhline( final, color = "r", linestyle = "--", label = "Value at N = %d" % counts[ -1 ] )
  pylab.axhspan( final * ( 1 - tolerance / 100.0 ), final * ( 1 + tolerance / 100.0 ),
                 color = "r", alpha = 0.12, label = "+/- %.1f%%" % tolerance )
  pylab.axvline( settle, color = "g", linestyle = ":", label = "Settles within tol. at N = %d" % settle )
  pylab.xscale( "log" )
  pylab.ticklabel_format( axis = "y", style = "sci", scilimits = ( 0, 0 ) )
  pylab.grid( True, which = "both", alpha = 0.4 )
  pylab.xlabel( "Number of measurements averaged" )
  pylab.ylabel( "Charge (C)" )
  pylab.title( title )
  pylab.legend( loc = 0, fontsize = 9 )

  fig.add_subplot( 212 )
  ns, rel = [], []
  for r in rows:
    if not np.isnan( r[ "std" ] ) and r[ "mean" ] != 0:
      ns.append( r[ "n" ] )
      rel.append( 100.0 * r[ "std" ] / abs( r[ "mean" ] ) )
  pylab.plot( ns, rel, "s-", color = "k" )
  pylab.xscale( "log" )
  pylab.yscale( "log" )
  pylab.grid( True, which = "both", alpha = 0.4 )
  pylab.xlabel( "Number of measurements averaged" )
  pylab.ylabel( "Spread between independent groups (% std)" )

  pylab.tight_layout()
  pylab.savefig( filename, dpi = 150 )
  pylab.close()


# ----------------------------------------------------------------------------
def parseador():
  parser = argparse.ArgumentParser( description = "Charge vs. number of averaged sweeps at a fixed position" )
  parser.add_argument( "-b", "--bulk", type = str, choices = [ "p", "n" ], default = "n", help = "bulk of sensor. Default = %(default)s", metavar = "" )
  parser.add_argument( "-c", "--channel", type = int, default = 1, help = "oscilloscope channel. Default = %(default)s", metavar = "" )
  parser.add_argument( "-v", "--voltage", type = str, default = "-100", help = "bias voltage. Default = %(default)s", metavar = "" )
  parser.add_argument( "-m", "--compliance", type = float, default = 2.5e-4, help = "compliance. Default = %(default)s", metavar = "" )
  parser.add_argument( "-n", "--num_measurements", type = int, default = 500, help = "raw sweeps to acquire. Default = %(default)s", metavar = "" )
  parser.add_argument( "-a", "--counts", type = int, nargs = "+", default = DEFAULT_COUNTS, help = "averaging numbers to evaluate", metavar = "" )
  parser.add_argument( "--mode", type = str, choices = [ "single", "normal" ], default = "single", help = "single: re-arm scope for every sweep; normal: free-running scope. Default = %(default)s", metavar = "" )
  parser.add_argument( "--delay", type = float, default = 0.2, help = "seconds to wait before each read. Default = %(default)s", metavar = "" )
  parser.add_argument( "--timeout", type = float, default = 30.0, help = "seconds to wait for a new sweep before aborting. Default = %(default)s", metavar = "" )
  parser.add_argument( "-f", "--file", type = str, default = None, help = "existing .bin file to analyze (skips acquisition)", metavar = "" )
  parser.add_argument( "--noise_file", type = str, default = None, help = "electronic noise .bin file. Default: electronicNoise_ch<N>.bin, then electronicNoise.bin", metavar = "" )
  parser.add_argument( "-t", "--tolerance", type = float, default = 1.0, help = "%% tolerance used to report the settling point. Default = %(default)s", metavar = "" )
  parser.add_argument( "-x", "--no_turn_off", action = "store_true", help = "do not turn off HV" )
  parser.add_argument( "-y", "--no_turn_on", action = "store_true", help = "do not control HV" )
  return parser.parse_args()


def main( args ):
  tag = "ch%d_V%s" % ( args.channel, args.voltage )
  # NOTE: the name deliberately avoids "scan2D" so analyzeScan2DR.py ignores it.
  filename = args.file if args.file else "sweepStudy_%s.bin" % tag

  if args.file is None:
    acquire( args, filename )

  noise_path = args.noise_file
  if noise_path is None:
    for cand in [ "electronicNoise_ch%d.bin" % args.channel, "electronicNoise.bin" ]:
      if os.path.exists( cand ):
        noise_path = cand
        break
  noise = loadNoise( noise_path, args.bulk )
  if noise is None:
    print( "WARNING: no electronic noise file found; charge is computed WITHOUT noise subtraction." )
  else:
    print( "Subtracting electronic noise from %s" % noise_path )

  waves, header = loadWaves( filename, args.bulk )
  duplicates = sum( 1 for i in range( 1, len( waves ) ) if np.array_equal( waves[ i ], waves[ i - 1 ] ) )
  if len( waves ) > 1 and duplicates == len( waves ) - 1:
    raise SystemExit( "ERROR: all %d waveforms in %s are identical, so the scope did not acquire "
                      "new sweeps. The results would be meaningless." % ( len( waves ), filename ) )
  if duplicates:
    print( "WARNING: %d sweeps are exact copies of the previous sweep." % duplicates )

  if noise is not None and len( noise ) != waves.shape[ 1 ]:
    common = min( len( noise ), waves.shape[ 1 ] )
    print( "WARNING: data waveforms have %d points but the noise waveform has %d; "
           "trimming both to %d points (dropping trailing samples)." % (
             waves.shape[ 1 ], len( noise ), common ) )
    waves = waves[ :, : common ]
    noise = noise[ : common ]

  total = len( waves )
  counts = sorted( set( [ n for n in args.counts if 1 <= n <= total ] ) )
  skipped = [ n for n in args.counts if n > total ]
  if skipped:
    print( "WARNING: file only has %d sweeps; skipping N = %s" % ( total, skipped ) )

  rows = analyze( waves, header, noise, counts )
  settle = settlingPoint( rows, args.tolerance )
  print( "\nFirst-N charge stays within %.1f%% of the N = %d value from N = %d onward." % (
    args.tolerance, counts[ -1 ], settle ) )

  base = filename.replace( ".bin", "" )
  writeTable( rows, base + "_results.txt" )
  plot( rows, args.tolerance, settle, base + ".png",
        "Charge vs. sweeps (ch %d, %s V)" % ( args.channel, args.voltage ) )
  print( "Saved %s_results.txt and %s.png" % ( base, base ) )


if __name__ == "__main__":
  main( parseador() )
