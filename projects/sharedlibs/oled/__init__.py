#!/usr/bin/env python3

#Python interface to the oledlib.so module.

from ctypes import CDLL, POINTER, c_float, c_ubyte

_lib = CDLL(__path__[0] + '/oledlib.so')

def startup(  ):
  _lib.Startup()

def shutdown(  ):
  _lib.Shutdown()

def display(  ):
  _lib.Display()

def seton( aTF ):
  _lib.SetOn(aTF)

def fill( aValue ):
  _lib.Fill(c_ubyte(aValue))

def clear(  ):
  _lib.Clear()

def pixel( aPos, aOn ):
  _lib.Pixel(*aPos, aOn)

def line( aStart, aEnd, aOn ):
  _lib.Line(*sStart, *eEnd, aOn)

