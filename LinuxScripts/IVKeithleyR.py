#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from OOHw.interface.InterfaceFactory import InterfaceFactory
import powerSupply as pW
import argparse
import time
import os

def iv( keithley, device, deviceType ):
  types = { "n" : -1, "p" : 1 }
  keithley.setAverage( 5 )
  compliance = 2.5e-4
  limit = 2.5e-4
  fd = open( "iv_%s.txt" % device, "w")
  for i in range( 0, 151, 3 ):
    pW.setPowerSupply( keithley, i * types[ deviceType ] , compliance )
    time.sleep( 3 )
    voltage = keithley.readVoltage()
    current = keithley.readCurrent()
    print "Voltage: %sV - Current: %suA" % ( voltage, str( float( current ) * 1e6 ) )
    fd.write( "%s\t%s\n" % ( voltage, current ) )
    fd.flush()
    os.fsync( fd.fileno() )
    if abs( float( current ) ) > limit:
      break
  fd.close()
  pW.turnOFFPowerSupply( keithley )

def parseador():
  parser = argparse.ArgumentParser( description = "IV Characterization with the K237 power supply." )
  parser.add_argument( "-d", "--device_name", type = str , required = True, help = "name of the device to characterize", metavar = "" )
  parser.add_argument( "-t", "--device_type", type = str , required = True, choices = [ "n", "p" ], help = "type of device. Choices=[n, p]", metavar = "" )
  args = parser.parse_args()
  return args

def main( device, deviceType ):
  factory = InterfaceFactory( "setupBrown.ini" )
  keithley = factory.getDevice( "highVoltage" )
  iv( keithley, device, deviceType )

if __name__ == "__main__":
  args = parseador()
  main( args.device_name, args.device_type )
