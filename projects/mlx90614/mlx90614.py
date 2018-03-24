'''IR temperature sensor using I2C interface.'''

import smbus

def c2f( aValue ):
  '''Celcius to Farenheit conversion.'''
  return (aValue * 9.0 / 5.0) + 32.0

class mlx(object):
  '''  '''

  _ADDRESS = 0x5A

  #RAM
#  _RAWIR1 = 0x04
#  _RAWIR2 = 0x05
  _TA = 0x06
  _TOBJ1 = 0x07
  _TOBJ2 = 0x08

  #EEPROM
#  _TOMAX = 0x20
#  _TOMIN = 0x21
#  _PWMCTRL = 0x22
#  _TARANGE = 0x23
#  _EMISS = 0x24
#  _CONFIG = 0x25
#  _ADDR = 0x0E
#  _ID1 = 0x3C
#  _ID2 = 0x3D
#  _ID3 = 0x3E
#  _ID4 = 0x3F

  def __init__(self):
    super(mlx, self).__init__()

    self._i2c = smbus.SMBus(1)

  def read( self, aLoc ) :
    '''Read 16 bit value and return.'''
    return self._i2c.read_word_data(mlx._ADDRESS, aLoc) #, addr_size = 16)

#  def write( self, aVal, aLoc ) :
#    """Write 16 bit value to given address.  aVal may be an int buffer."""
#    self._i2c.write_word_data(_ADDRESS, aLoc, aVal)

  def readtemp( self, aLoc ) :
    ''' '''
    temp = self.read(aLoc)
    return (temp * 0.02) - 273.15

  def ambienttemp( self ) :
    return self.readtemp(mlx._TA)

  def objecttemp( self ) :
    return self.readtemp(mlx._TOBJ1)

  def object2temp( self ) :
    return self.readtemp(mlx._TOBJ2)
