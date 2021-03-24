#!/usr/bin/env python3

from smbus import SMBus

class mcp(object):
  """Driver for mcp4725 DAC."""

  _ADDRESS = 0x62
  _WRITEDAC = 0x40        #Write data directly to DAC.
  _WRITEDACEEPROM = 0x60  #Write data to DAC and to EEPROM for persistent value accross resets.

  def __init__( self ):
    super(mcp, self).__init__()
    self._i2c = SMBus(1)
    self._buffer = [0, 0]

  def set( self, aValue ):
    ''' Set the DAC to the given value which is only 12 bits in size (0xFFF). '''

    self._buffer[0] = aValue >> 4
    self._buffer[1] = (aValue & 0xF) << 4
    self._i2c.write_i2c_block_data(mcp._ADDRESS, mcp._WRITEDAC, self._buffer)

