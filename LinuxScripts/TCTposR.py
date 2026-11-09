#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import sys
import math
import shutil
import argparse
import time
import datetime
import numpy as np
from OOHw.interface.InterfaceFactory import InterfaceFactory
from OOHw.files.BINWriter import BINWriter
import powerSupply as pW
import vxi11
import analyzeDataR as aD
from TCTData import TCTData
import stages
import coordinatesFile as cF

SENSORS = [ "First", "Second", "Third", "Fourth" ]
RESULTS_FILE = "positionScan_results.txt"
RESULTS_HEADER = "Sensor\tChannel\tBias(V)\tLaserX\tLaserY\tSensorX\tSensorY\tDistance\tCharge(C)\tFile\n"


# ---------------------------------------------------------------- sensor positions
# Sensor coordinates live in the same coordinates file used by focusR and
# currentPositionR (sensors.txt, through coordinatesFile).

def loadPositions():
    """Sensor x, y positions { name: [ x, y ] or None }, read from the coordinates file."""
    sensors = cF.getCoordFromFile()
    positions = {}
    for s in SENSORS:
        if s in sensors and sensors[ s ] is not None:
            positions[ s ] = [ float( sensors[ s ][ 0 ] ), float( sensors[ s ][ 1 ] ) ]
        else:
            positions[ s ] = None
    return positions

def setSensorPosition( sensor, x, y ):
    """Update x, y of a sensor in the coordinates file; z is left as it is.
       Same steps as writeNewCoord in focusR."""
    shutil.copyfile( "sensors.txt", "sensors_back.txt" )
    sensors = cF.getCoordFromFile()
    X, Y, Z = sensors[ sensor ]
    sensors = cF.changeCoordinate( sensors, sensor, x, y, Z )
    sensors = cF.setCoordHoldSyst( sensors )
    cF.writeCoord2File( sensors )

def printPositions( positions ):
    print "Stored sensor positions (x, y):"
    for s in SENSORS:
        if positions[ s ] is None:
            print "  %-7s not set" % s
        else:
            print "  %-7s x = %s  y = %s" % ( s, positions[ s ][ 0 ], positions[ s ][ 1 ] )


# ---------------------------------------------------------------- laser position

def readLaserPosition():
    """Current relative x, y of the laser, read from the stages (as in currentPositionR)."""
    s = stages.open_socket()
    try:
        X, Y, Z = stages.getRelativeCoordinates( s )
    finally:
        stages.close_socket( s )
    return float( X ), float( Y )


# ---------------------------------------------------------------- acquisition

def safeObtainPreamble( scope, channel, retries = 20, delay = .5 ):
    for attempt in range( retries ):
        try:
            return scope.obtainPreamble( channel )
        except ( KeyError, vxi11.vxi11.Vxi11Exception ) as e:
            if attempt == retries - 1:
                raise
            print "safeObtainPreamble retry %d/%d after %s" % ( attempt + 1, retries, e )
            time.sleep( delay )

def acquireOne( scope, files, channels, averageNumber ):
    """One averaged waveform per channel. files maps channel ("F1") -> .bin path."""
    writers = {}
    for channel in channels:
        writers[ channel ] = BINWriter( files[ channel ] )
    scope.clearSweeps()
    while safeObtainPreamble( scope, channels[ 0 ] )[ "SWEEPS_PER_ACQ" ] != str( averageNumber ):
        print "Sweeps: %s/%s" % ( safeObtainPreamble( scope, channels[ 0 ] )[ "SWEEPS_PER_ACQ" ], averageNumber )
        time.sleep( .5 )
    for channel in channels:
        waveform, points, bytesPoint = scope.readWaveformBIN( channel )
        binwriter = writers[ channel ]
        binwriter.header = scope.preamble
        binwriter.bytesPerPoint( bytesPoint )
        binwriter.pointsPerMeasurement( points )
        binwriter.addData( waveform )
    for binwriter in writers.values():
        binwriter.writeData()
        binwriter.close()

def confScope( scope, channels ):
    for channel in channels:
        scope.channel = "C" + str( channel )
        scope.function = "F" + str( channel )
        scope.coupling( scope.channel, "D50" )
        scope.trace( scope.channel, "ON" )
        scope.trace( scope.function, "ON" )

def setAverage( scope, channels, average_number ):
    for channel in channels:
        scope.channel = "C" + str( channel )
        scope.function = "F" + str( channel )
        scope.average( str( average_number ) )


# ---------------------------------------------------------------- analysis

class ZeroNoise( object ):
    """Stand-in for the electronic noise file: subtracts nothing."""
    pass

def analyzeFile( filename, bulk, plots ):
    """Same steps as analyzeDataR.processData without a noise file.
       The charge is the integral of the negative lobe of the averaged waveform."""
    dataTCT = TCTData( filename )
    dataTCT.bulk = bulk
    aD.getData( dataTCT )
    aD.convertAndShiftData( dataTCT )
    noise = ZeroNoise()
    noise.ydata = [ np.zeros_like( np.array( dataTCT.ydata[ 0 ] ) ) ]
    aD.removeElectronicNoise( dataTCT, noise )
    aD.averageTheData( dataTCT )
    aD.cutData( dataTCT, "signal" )
    charge = aD.getCharge( dataTCT )
    if plots:
        aD.plotAnalysis( dataTCT )
    return charge


# ---------------------------------------------------------------- user input

def askSensorMap( channels ):
    """Ask which sensor is connected to each scope channel."""
    mapping = {}
    for ch in channels:
        while True:
            answer = raw_input( "Which sensor is connected to channel %d? (%s): " % ( ch, " / ".join( SENSORS ) ) ).strip().capitalize()
            if answer not in SENSORS:
                print "  Please answer with one of: %s" % ", ".join( SENSORS )
            elif answer in mapping.values():
                print "  %s is already assigned to another channel" % answer
            else:
                mapping[ ch ] = answer
                break
    return mapping

def parseador():
    parser = argparse.ArgumentParser( description = "TCT measurement at the current laser position, with analysis" )
    parser.add_argument( "-n", "--acquisition_number", type = int, default = 1, help = "number of acquisitions = number of .bin files per channel. Default = %(default)s", metavar = "" )
    parser.add_argument( "-g", "--average_number", type = int, default = 512, help = "number of waveforms averaged in each acquisition. Default = %(default)s", metavar = "" )
    parser.add_argument( "-c", "--channel", type = str, default = "1", help = "scope channel(s); comma-separated for multi-channel, e.g. '1,4'. Default = %(default)s", metavar = "" )
    parser.add_argument( "-v", "--voltage", type = float, default = 0, help = "bias voltage in V. Default = %(default)s", metavar = "" )
    parser.add_argument( "-m", "--compliance", type = float, default = 10e-6, help = "compliance of the HV power supply in A. Default = %(default)s", metavar = "" )
    parser.add_argument( "-b", "--bulk", type = str, choices = [ "p", "n" ], help = "bulk of the sensor. Choices = n, p", metavar = "" )
    parser.add_argument( "-i", "--intensity", type = str, default = "0", help = "laser intensity in %%. Default = %(default)s", metavar = "" )
    parser.add_argument( "-t", "--temperature", type = str, default = "32", help = "temperature in F. Default = %(default)s", metavar = "" )
    parser.add_argument( "-f", "--filename", type = str, default = "TCT", help = "base name of the binary files. Default = %(default)s", metavar = "" )
    parser.add_argument( "-X", "--laser_x", type = float, help = "laser x position (overrides the stage reading; needs -Y)", metavar = "" )
    parser.add_argument( "-Y", "--laser_y", type = float, help = "laser y position (overrides the stage reading)", metavar = "" )
    parser.add_argument( "-p", "--set_position", nargs = 3, action = "append", metavar = ( "SENSOR", "X", "Y" ), help = "set the x, y position of a sensor (First/Second/Third/Fourth) in the coordinates file and exit. Can be repeated" )
    parser.add_argument( "-s", "--show_positions", action = "store_true", help = "print the stored sensor positions and exit" )
    parser.add_argument( "--plots", action = "store_true", help = "save the analysis check plots (png) next to each .bin file" )
    parser.add_argument( "-x", "--no_turn_off", action = "store_true", help = "do not turn off the power supply at the end" )
    parser.add_argument( "-z", "--turn_off", action = "store_true", help = "turn off the power supply and exit" )
    args = parser.parse_args()

    args.channels = [ int( ch.strip() ) for ch in args.channel.split( "," ) if ch.strip() != "" ]
    if args.set_position:
        for sensor, x, y in args.set_position:
            if sensor.capitalize() not in SENSORS:
                parser.error( "sensor must be one of %s" % ", ".join( SENSORS ) )
            try:
                float( x ); float( y )
            except ValueError:
                parser.error( "sensor position needs numeric x and y" )
    if not ( args.set_position or args.show_positions or args.turn_off ):
        if not args.bulk:
            parser.error( "--bulk is required" )
        if args.voltage > 0 and args.bulk == "n":
            parser.error( "n bulk requires negative voltage" )
        if args.voltage < 0 and args.bulk == "p":
            parser.error( "p bulk requires positive voltage" )
        if args.acquisition_number < 1 or args.average_number < 1:
            parser.error( "--acquisition_number and --average_number must be >= 1" )
        if len( args.channels ) < 1 or len( args.channels ) > len( SENSORS ):
            parser.error( "give between 1 and %d channels" % len( SENSORS ) )
        if ( args.laser_x is None ) != ( args.laser_y is None ):
            parser.error( "give both -X and -Y, or neither" )
    return args


# ---------------------------------------------------------------- main

def main():
    t1 = time.time()
    args = parseador()

    if args.turn_off:
        factory = InterfaceFactory( "setupBrown.ini" )
        pW.turnOFFPowerSupply( factory.getDevice( "highVoltage" ) )
        return

    positions = loadPositions()

    # Update / show stored sensor positions
    if args.set_position:
        for sensor, x, y in args.set_position:
            setSensorPosition( sensor.capitalize(), int( round( float( x ) ) ), int( round( float( y ) ) ) )
        positions = loadPositions()
    if args.set_position or args.show_positions:
        printPositions( positions )
        return

    # Laser position
    if args.laser_x is not None:
        laserX, laserY = args.laser_x, args.laser_y
    else:
        laserX, laserY = readLaserPosition()

    # Which sensor is on which channel
    sensorMap = askSensorMap( args.channels )
    for ch in args.channels:
        if positions[ sensorMap[ ch ] ] is None:
            sys.exit( "Position of the %s sensor is not in the coordinates file. Use: -p %s X Y" % ( sensorMap[ ch ], sensorMap[ ch ] ) )
    print "\nLaser at x = %s, y = %s" % ( laserX, laserY )
    for ch in args.channels:
        print "Channel %d -> %s sensor" % ( ch, sensorMap[ ch ] )

    stamp = datetime.datetime.fromtimestamp( time.time() ).strftime( "%Y-%m-%d_%H:%M:%S" )
    base = "%s_X%s_Y%s_V%sV_T%sF_I%s_%s" % ( args.filename, laserX, laserY, args.voltage, args.temperature, args.intensity, stamp )
    channels = [ "F" + str( ch ) for ch in args.channels ]
    recorded = []  # ( channel number, sensor, bin path )

    factory = InterfaceFactory( "setupBrown.ini" )
    scope = factory.getDevice( "scope" )
    keithley = factory.getDevice( "highVoltage" )
    try:
        pW.setPowerSupply( keithley, str( args.voltage ), args.compliance )
        confScope( scope, args.channels )
        setAverage( scope, args.channels, args.average_number )
        scope.controlAcquisition( "AUTO" )
        for i in range( 1, args.acquisition_number + 1 ):
            files = {}
            for ch in args.channels:
                path = os.path.join( os.getcwdu(), "%s_%s_ch%d_%03d.bin" % ( base, sensorMap[ ch ], ch, i ) )
                files[ "F" + str( ch ) ] = path
                recorded.append( ( ch, sensorMap[ ch ], path ) )
            print "Acquisition %d/%d" % ( i, args.acquisition_number )
            acquireOne( scope, files, channels, args.average_number )
    finally:
        if not args.no_turn_off:
            pW.turnOFFPowerSupply( keithley )

    # Analysis
    rows = []
    for ch, sensor, path in recorded:
        charge = analyzeFile( path, args.bulk, args.plots )
        sx, sy = positions[ sensor ]
        distance = math.sqrt( ( laserX - sx ) ** 2 + ( laserY - sy ) ** 2 )
        print "%s (ch%d): charge = %e C, distance = %s" % ( sensor, ch, charge, distance )
        rows.append( "%s\t%d\t%s\t%s\t%s\t%s\t%s\t%s\t%e\t%s\n" % ( sensor, ch, args.voltage, laserX, laserY, sx, sy, distance, charge, os.path.basename( path ) ) )
    aD.writeResults( os.path.join( os.getcwdu(), RESULTS_FILE ), RESULTS_HEADER, rows )
    print "Results appended to %s" % RESULTS_FILE
    print time.time() - t1


if __name__ == "__main__":
    main()
