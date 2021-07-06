#!/usr/bin/env python3
# pca9685 servo controller driver.

from ctypes import CDLL, c_bool, c_float

# Located in usr/local/bin
_lib = CDLL(__path__[0] + '/pca9685lib.so')

#--------------------------------------------------------
def startup(  ):
  ''' Initialize the singleton version of the system. '''
  b = c_bool(_lib.Startup())
  return b.value

#--------------------------------------------------------
def isgood(  ):
  ''' Returns true if the system is setup successfully. '''
  b = c_bool(_lib.IsGood())
  return b.value

#--------------------------------------------------------
def shutdown(  ):
  ''' Shut down the singleton instance of this system. '''
  _lib.Shutdown()

#--------------------------------------------------------
def setfreq( aFreq ):
  ''' Set the PWM signal frequency. '''
  _lib.SetFreq(aFreq)

#--------------------------------------------------------
def setpwm( aIndex, aOn, aOff = 4095 ):
  ''' Set PWM on/off values for given index. Values from 0-4095.
      if aOn is a float, the values are set to 0.0,aOff * aOn to allow
      for setting pwm based on percentage.
      IE: setpwm(0, 10, 2048) = set pwm on/off for index 0 to 10,2048
          setpwm(0, 0, 100) = set pwm on/off to 100,4095
          setpwm(0, 0.75) = set pwm on/off to 0,4095 * 0.75
          setpwm(0, 0.5, 2048) = set pwm to 0,2048 * 0.5
       '''
  #if aOn is a float, assume we are setting a percentage and ignore aOff.
  if type(aOn) == float:
    aOff = int(aOff * aOn)
    aOn = 0

  _lib.SetPWM(aIndex, aOn, aOff)

#--------------------------------------------------------
def off( aIndex ):
  ''' Turn given index off. '''
  _lib.Off(aIndex)

#--------------------------------------------------------
def alloff(  ):
  ''' Turn all slots off. '''
  _lib.AllOff()

#--------------------------------------------------------
def set( aIndex, aValue ):
  ''' Set index to value 0.0 - 1.0 using servo value ranges. '''
  _lib.Set(aIndex, c_float(aValue))

#--------------------------------------------------------
def setangle( aIndex, aAngle ):
  ''' Set index to angle -90.0 - 90.0. '''
  _lib.SetAngle(aIndex, c_float(aAngle))

#automatically start it up and eat the return value.
_ = startup()