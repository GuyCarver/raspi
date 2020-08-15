#driver for Sainsmart 1.8" TFT display ST7735
#Translated by Guy Carver from the ST7735 sample code.

from math import sqrt
import numbers
import time

import numpy

from PIL import Image
from PIL import ImageDraw

from PIL import ImageFont

import Adafruit_GPIO as GPIO
import Adafruit_GPIO.SPI as SPI

def clamp( aValue, aMin, aMax ) :
  return max(aMin, min(aMax, aValue))

ScreenSize = (128, 160)

class ST7735(object) :
  """Sainsmart TFT 7735 display driver."""

  #TFTRotations and TFTRGB are bits to set
  # on MADCTL to control display rotation/color layout
  #Looking at display with pins on top.
  #00 = upper left printing right
  #10 = does nothing (MADCTL_ML)
  #20 = upper left printing down (backwards) (Vertical flip)
  #40 = upper right printing left (backwards) (X Flip)
  #80 = lower left printing right (backwards) (Y Flip)
  #04 = (MADCTL_MH)

  #60 = 90 right rotation
  #C0 = 180 right rotation
  #A0 = 270 right rotation
  Rotations = [0x00, 0x60, 0xC0, 0xA0]
  BGR = 0x08 #When set color is bgr else rgb.
  RGB = 0x00

  SPI_HZ = 4000000 # 4 MHz

  NOP = 0x0
  SWRESET = 0x01
  RDDID = 0x04
  RDDST = 0x09

  SLPIN  = 0x10
  SLPOUT  = 0x11
  PTLON  = 0x12
  NORON  = 0x13

  INVOFF = 0x20
  INVON = 0x21
  DISPOFF = 0x28
  DISPON = 0x29
  CASET = 0x2A
  RASET = 0x2B
  RAMWR = 0x2C
  RAMRD = 0x2E

  COLMOD = 0x3A
  MADCTL = 0x36

  FRMCTR1 = 0xB1
  FRMCTR2 = 0xB2
  FRMCTR3 = 0xB3
  INVCTR = 0xB4
  DISSET5 = 0xB6

  PWCTR1 = 0xC0
  PWCTR2 = 0xC1
  PWCTR3 = 0xC2
  PWCTR4 = 0xC3
  PWCTR5 = 0xC4
  VMCTR1 = 0xC5

  RDID1 = 0xDA
  RDID2 = 0xDB
  RDID3 = 0xDC
  RDID4 = 0xDD

  PWCTR6 = 0xFC

  GMCTRP1 = 0xE0
  GMCTRN1 = 0xE1

  BLACK = (0,0,0)
  RED = (0xFF, 0x00, 0x00)
  MAROON = (0x80, 0x00, 0x00)
  GREEN = (0x00, 0xFF, 0x00)
  FOREST = (0x00, 0x80, 0x80)
  BLUE = (0x00, 0x00, 0xFF)
  NAVY = (0x00, 0x00, 0x80)
  CYAN = (0x00, 0xFF, 0xFF)
  YELLOW = (0xFF, 0xFF, 0x00)
  PURPLE = (0xFF, 0x00, 0xFF)
  WHITE = (0xFF, 0xFF, 0xFF)
  GRAY = (0x80, 0x80, 0x80)

  def img2data( image ) :
    """Generator function to convert a PIL image to 16-bit 565 RGB bytes."""
    # NumPy is much faster at doing this. NumPy code provided by:
    # Keith (https://www.blogger.com/profile/02555547344016007163)
    pb = numpy.array(image.convert('RGB')).astype('uint16')
    color = ((pb[:,:,0] & 0xF8) << 8) | ((pb[:,:,1] & 0xFC) << 3) | (pb[:,:,2] >> 3)
    return numpy.dstack(((color >> 8) & 0xFF, color & 0xFF)).flatten().tolist()

  def __init__( self, aSPI, aDC, aReset = None, aGPIO = None ) :
    """aLoc SPI pin location is either 1 for 'X' or 2 for 'Y'.
       aDC is the DC pin and aReset is the reset pin."""
    self._rotate = 0                            #Vertical with top toward pins.
    self._rgb = True                            #color order of rgb.
    self._on = True
    self._dc  = aDC
    self._rst = aReset
    self._spi = aSPI
    self._gpio = aGPIO
    if self._gpio == None :
      self._gpio = GPIO.get_platform_gpio()

    if self._rst != None :
      self._gpio.setup(self._rst, GPIO.OUT)

    # Set DC as output.
    self._gpio.setup(self._dc, GPIO.OUT)

    self._spi.set_mode(0)
    self._spi.set_bit_order(SPI.MSBFIRST)
    self._spi.set_clock_hz(ST7735.SPI_HZ)

    self._oneData = [0]
    self._windowLocData = [0, 0, 0, 0]

    # Create an image buffer.
    self._buffer = Image.new('RGB', ScreenSize)

  @property
  def size( self ) :
    return self._buffer.size

  @property
  def surface( self ) :
    """Return a PIL ImageDraw instance for 2D drawing on the image buffer."""
    return ImageDraw.Draw(self._buffer)

  @property
  def buffer( self ) :
    return self._buffer

  @property
  def rotate( self ) :
    return self.rotate

  @rotate.setter
  def rotate( self, aRot ) :
    '''0 - 3. Starts vertical with top toward pins and rotates 90 deg
       clockwise each step.'''
    aRot &= 0x03
    rotchange = self._rotate ^ aRot
    if rotchange :
      self._rotate = aRot
      #If switching from vertical to horizontal swap x,y
      # (indicated by bit 0 changing).
      if (rotchange & 1):
        self._buffer.size =(self.buffer.size[1], self._buffer.size[0])
      self._setMADCTL()

  @property
  def command( self ) :
    return None

  @command.setter
  def command( self, aCommand ) :
    '''Write given command to the device.'''
    self._write(aCommand, False)

  @property
  def data( self ) :
    return None

  @data.setter
  def data( self, aData ) :
    '''Write given data to the device.'''
    self._write(aData)

  @property
  def on( self ) :
    return self._on

  @on.setter
  def on( self, aTF ) :
    '''Turn display on or off.'''
    self._on = aTF
    self.command = ST7735.DISPON if aTF else ST7735.DISPOFF

  @property
  def invertcolor( self ) :
    return self._invertcolor

  @invertcolor.setter
  def invertcolor( self, aTF ) :
    self._invertcolor = aTF
    '''Invert the color data IE: Black = White.'''
    self.command = ST7735.INVON if aTF else ST7735.INVOFF

  @property
  def rgb( self ) :
    return self._rgb

  @rgb.setter
  def rgb( self, aTF ) :
    '''True = rgb else bgr'''
    self._rgb = aTF
    self._setMADCTL()

  def set_window(self, x0=0, y0=0, x1=None, y1=None):
    """Set the pixel address window for succeeding drawing commands. x0 and
    x1 should define the minimum and maximum x pixel bounds.  y0 and y1
    should define the minimum and maximum y pixel bound.  If no parameters
    are specified the default will be to update the entire display from 0,0
    to width-1,height-1.
    """
    if x1 is None:
        x1 = self.size[0] - 1
    if y1 is None:
        y1 = self.size[1] - 1
    self.command = ST7735.CASET                 # Column addr set
    self._windowLocData[0] = x0 >> 8
    self._windowLocData[1] = x0                 # XSTART
    self._windowLocData[2] = x1 >> 8
    self._windowLocData[3] = x1                 # XEND
    self.data = self._windowLocData
    self.command = ST7735.RASET                 # Row addr set
    self._windowLocData[0] = y0 >> 8
    self._windowLocData[1] = y0                 # YSTART
    self._windowLocData[2] = y1 >> 8
    self._windowLocData[3] = y1                 # YEND
    self.data = self._windowLocData
    self.command = ST7735.RAMWR               # write to RAM

  def _write( self, data, isData = True, chunkSize = 4096 ) :
    """Write a byte or array of bytes to the display. Is_data parameter
    controls if byte should be interpreted as display data (True) or command
    data (False).  Chunk_size is an optional size of bytes to write in a
    single SPI transaction, with a default of 4096.
    """
    # Set DC low for command, high for data.
    self._gpio.output(self._dc, isData)
    # Convert scalar argument to list so either can be passed as parameter.
    if isinstance(data, numbers.Number):
      self._oneData[0] = data & 0xFF
      data = self._oneData

    # Write data a chunk at a time.
    for start in range(0, len(data), chunkSize):
      end = min(start + chunkSize, len(data))
      self._spi.write(data[start:end])


  def _setMADCTL( self ) :
    '''Set screen rotation and RGB/BGR format.'''
    self.command = ST7735.MADCTL
    rgb = ST7735.RGB if self._rgb else ST7735.BGR
    self.data = ST7735.Rotations[self._rotate] | rgb

  def reset( self ) :
    """Reset the display, if reset pin is connected."""
    if self._rst is not None:
      self._gpio.output(self._dc, False)
      self._gpio.set_high(self._rst)
      time.sleep(0.500)
      self._gpio.set_low(self._rst)
      time.sleep(0.500)
      self._gpio.set_high(self._rst)
      time.sleep(0.500)

  def fill( self, aColor = BLACK ) :
    """Fill buffer with color (default = black)."""
    w, h = self._buffer.size
    self._buffer.putdata([aColor] * (w * h))

  def display(self, image=None):
    """Write the display buffer or provided image to the hardware.  If no
    image parameter is provided the display buffer will be written to the
    hardware.  If an image is provided, it should be RGB format and the
    same dimensions as the display hardware.
    """
    # By default write the internal buffer to the display.
    if image is None:
      image = self._buffer
    # Set address bounds to entire display.
    self.set_window()
    # Convert image to array of 16bit 565 RGB data bytes.
    # Unfortunate that this copy has to occur, but the SPI byte writing
    # function needs to take an array of bytes and PIL doesn't natively
    # store images in 16-bit 565 RGB format.
    self.data = list(ST7735.img2data(image))

  def initb( self ) :
    '''Initialize blue tab version.'''
#    self._size = (ScreenSize[0] + 2, ScreenSize[1] + 1)
    self.reset()
    self.command = ST7735.SWRESET               #Software reset.
    time.sleep(.150)
    self.command = ST7735.SLPOUT                #out of sleep mode.
    time.sleep(.500)

    self.command = ST7735.COLMOD                #Set color mode.
    self.data = 0x05                            #16 bit color.
#    pyb.delay(10)

    data3 = [0x00, 0x06, 0x03]                  #fastest refresh, 6 lines front, 3 lines back.
    self.command = ST7735.FRMCTR1               #Frame rate control.
    self.data = data3
#    pyb.delay(10)

    self.command = ST7735.MADCTL
    self.data = 0x08                            #row address/col address, bottom to top refresh

    self.command = ST7735.DISSET5               #Display settings
    data2 = [0x15, 0x02]                        #1 clock cycle nonoverlap, 2 cycle gate rise, 3 cycle oscil, equalize
                                                #fix on VTL
    self.data = data2

    self.command = ST7735.INVCTR                #Display inversion control
    self.data = 0x00                            #Line inversion.

    self.command = ST7735.PWCTR1                #Power control
    data2[0] = 0x02   #GVDD = 4.7V
    data2[1] = 0x70   #1.0uA
    self.data = data2
#    pyb.delay(10)

    self.command = ST7735.PWCTR2                #Power control
    self.data = 0x05                            #VGH = 14.7V, VGL = -7.35V

    self.command = ST7735.PWCTR3                #Power control
    data2[0] = 0x01   #Opamp current small
    data2[1] = 0x02   #Boost frequency
    self.data = data2

    self.command = ST7735.VMCTR1               #Power control
    data2[0] = 0x3C   #VCOMH = 4V
    data2[1] = 0x38   #VCOML = -1.1V
    self.data = data2
#    pyb.delay(10)

    self.command = ST7735.PWCTR6               #Power control
    data2[0] = 0x11
    data2[1] = 0x15
    self.data = data2

    #These different values don't seem to make a difference.
#     dataGMCTRP = bytearray([0x0f, 0x1a, 0x0f, 0x18, 0x2f, 0x28, 0x20, 0x22, 0x1f,
#                             0x1b, 0x23, 0x37, 0x00, 0x07, 0x02, 0x10])
    dataGMCTRP = [0x02, 0x1c, 0x07, 0x12, 0x37, 0x32, 0x29, 0x2d, 0x29,
                            0x25, 0x2b, 0x39, 0x00, 0x01, 0x03, 0x10]
    self.command = ST7735.GMCTRP1
    self.data = dataGMCTRP

#     dataGMCTRN = bytearray([0x0f, 0x1b, 0x0f, 0x17, 0x33, 0x2c, 0x29, 0x2e, 0x30,
#                             0x30, 0x39, 0x3f, 0x00, 0x07, 0x03, 0x10])
    dataGMCTRN = [0x03, 0x1d, 0x07, 0x06, 0x2e, 0x2c, 0x29, 0x2d, 0x2e,
                            0x2e, 0x37, 0x3f, 0x00, 0x00, 0x02, 0x10]
    self.command = ST7735.GMCTRN1
    self.data = dataGMCTRN
#    pyb.delay(10)

    self.command = ST7735.CASET                 #Column address set.
    self._windowLocData[0] = 0x00
    self._windowLocData[1] = 2                  #Start at column 2
    self._windowLocData[2] = 0x00
    self._windowLocData[3] = self.size[0] - 1
    self.data = self._windowLocData

    self.command = ST7735.RASET                 #Row address set.
    self._windowLocData[1] = 1                  #Start at row 2.
    self._windowLocData[3] = self.size[1] - 1
    self.data = self._windowLocData

    self.command = ST7735.NORON                 #Normal display on.
#    pyb.delay(10)

    self.command = ST7735.RAMWR
#    pyb.delay(500)

    self.command = ST7735.DISPON
    self.cs.high()
#    pyb.delay(500)

  def initr( self ) :
    '''Initialize a red tab version.'''
    self.reset()

    self.command = ST7735.SWRESET               #Software reset.
    time.sleep(0.15)
    self.command = ST7735.SLPOUT                #out of sleep mode.
    time.sleep(0.5)

    data3 = bytearray([0x01, 0x2C, 0x2D])       #fastest refresh, 6 lines front, 3 lines back.
    self.command = ST7735.FRMCTR1               #Frame rate control.
    self.data = data3

    self.command = ST7735.FRMCTR2               #Frame rate control.
    self.data = data3

    data6 = bytearray([0x01, 0x2c, 0x2d, 0x01, 0x2c, 0x2d])
    self.command = ST7735.FRMCTR3               #Frame rate control.
    self.data = data6
#    pyb.delay(10)

    data1 = bytearray(1)
    self.command = ST7735.INVCTR                #Display inversion control
    data1[0] = 0x07                             #Line inversion.
    self.data = data1

    self.command = ST7735.PWCTR1                #Power control
    data3[0] = 0xA2
    data3[1] = 0x02
    data3[2] = 0x84
    self.data = data3

    self.command = ST7735.PWCTR2                #Power control
    data1[0] = 0xC5   #VGH = 14.7V, VGL = -7.35V
    self.data = data1

    data2 = bytearray(2)
    self.command = ST7735.PWCTR3                #Power control
    data2[0] = 0x0A   #Opamp current small
    data2[1] = 0x00   #Boost frequency
    self.data = data2

    self.command = ST7735.PWCTR4                #Power control
    data2[0] = 0x8A   #Opamp current small
    data2[1] = 0x2A   #Boost frequency
    self.data = data2

    self.command = ST7735.PWCTR5                #Power control
    data2[0] = 0x8A   #Opamp current small
    data2[1] = 0xEE   #Boost frequency
    self.data = data2

    self.command = ST7735.VMCTR1                #Power control
    data1[0] = 0x0E
    self.data = data1

    self.command = ST7735.INVOFF

    self.command = ST7735.MADCTL                #Power control
    data1[0] = 0xC8
    self.data = data1

    self.command = ST7735.COLMOD
    data1[0] = 0x05
    self.data = data1

    self.command = ST7735.CASET                 #Column address set.
    self._windowLocData[0] = 0x00
    self._windowLocData[1] = 0x00
    self._windowLocData[2] = 0x00
    self._windowLocData[3] = self.size[0] - 1
    self.data = self._windowLocData

    self.command = ST7735.RASET                 #Row address set.
    self._windowLocData[3] = self.size[1] - 1
    self.data = self._windowLocData

    dataGMCTRP = bytearray([0x0f, 0x1a, 0x0f, 0x18, 0x2f, 0x28, 0x20, 0x22, 0x1f,
                            0x1b, 0x23, 0x37, 0x00, 0x07, 0x02, 0x10])
    self.command = ST7735.GMCTRP1
    self.data = dataGMCTRP

    dataGMCTRN = bytearray([0x0f, 0x1b, 0x0f, 0x17, 0x33, 0x2c, 0x29, 0x2e, 0x30,
                            0x30, 0x39, 0x3f, 0x00, 0x07, 0x03, 0x10])
    self.command = ST7735.GMCTRN1
    self.data = dataGMCTRN
#    pyb.delay(10)

    self.command = ST7735.DISPON
#    pyb.delay(100)

    self.command = ST7735.NORON                 #Normal display on.
#    pyb.delay(10)

    self.cs.high()

  def initg( self ) :
    '''Initialize a green tab version.'''
    self.reset()

    self.command = ST7735.SWRESET               #Software reset.
    time.sleep(0.15)
    self.command = ST7735.SLPOUT                #out of sleep mode.
    time.sleep(0.5)

    #NOTE: May not need to make this a byte array.  Try just the list or a tuple.
    data3 = [0x01, 0x2C, 0x2D]                  #fastest refresh, 6 lines front, 3 lines back.
    self.command = ST7735.FRMCTR1               #Frame rate control.
    self.data = data3

    self.command = ST7735.FRMCTR2               #Frame rate control.
    self.data = data3

    data6 = [0x01, 0x2c, 0x2d, 0x01, 0x2c, 0x2d]
    self.command = ST7735.FRMCTR3               #Frame rate control.
    self.data = data6
#    pyb.delay(10)

    self.command = ST7735.INVCTR                #Display inversion control
    self.data = 0x07

    self.command = ST7735.PWCTR1                #Power control
    data3[0] = 0xA2
    data3[1] = 0x02
    data3[2] = 0x84
    self.data = data3

    self.command = ST7735.PWCTR2                #Power control
    self.data = 0xC5

    self.command = ST7735.PWCTR3                #Power control
    data2 = [0x0A, 0x00]   #Opamp current small, Boost frequency
    self.data = data2

    self.command = ST7735.PWCTR4                #Power control
    data2[0] = 0x8A   #Opamp current small
    data2[1] = 0x2A   #Boost frequency
    self.data = data2

    self.command = ST7735.PWCTR5                #Power control
    data2[0] = 0x8A   #Opamp current small
    data2[1] = 0xEE   #Boost frequency
    self.data = data2

    self.command = ST7735.VMCTR1                #Power control
    self.data = 0x0E

    self.command = ST7735.INVOFF

    self._setMADCTL()

    self.command = ST7735.COLMOD
    self.data = 0x05

    self.command = ST7735.CASET                 #Column address set.
    self._windowLocData[0] = 0x00
    self._windowLocData[1] = 0x01                #Start at row/column 1.
    self._windowLocData[2] = 0x00
    self._windowLocData[3] = self.size[0] - 1
    self.data = self._windowLocData

    self.command = ST7735.RASET                 #Row address set.
    self._windowLocData[3] = self.size[1] - 1
    self.data = self._windowLocData

    dataGMCTRP = [0x02, 0x1c, 0x07, 0x12, 0x37, 0x32, 0x29, 0x2d, 0x29,
                            0x25, 0x2b, 0x39, 0x00, 0x01, 0x03, 0x10]
    self.command = ST7735.GMCTRP1
    self.data = dataGMCTRP

    dataGMCTRN = [0x03, 0x1d, 0x07, 0x06, 0x2e, 0x2c, 0x29, 0x2d, 0x2e,
                            0x2e, 0x37, 0x3f, 0x00, 0x00, 0x02, 0x10]
    self.command = ST7735.GMCTRN1
    self.data = dataGMCTRN

    self.command = ST7735.NORON                 #Normal display on.
    time.sleep(0.10) # 10 ms

    self.command = ST7735.DISPON
    time.sleep(0.100) # 100 ms

def makeg(  ) :
#  def __init__( self, aSPI, aDC, aReset = None, aGPIO = None ) :
  #port, device
  s = SPI.SpiDev(0, 0, max_speed_hz=4000000)
  t = ST7735(s, 24, 25)
  t.initg()
  t.fill(0)
  t.display()
  return t

def Elipse( surface ) :
  # Draw some shapes.
  # Draw a blue ellipse with a green outline.
  surface.ellipse((10, 10, 110, 80), outline=(0,255,0), fill=(0,0,255))

def Rect( surface ) :
  # Draw a purple rectangle with yellow outline.
  surface.rectangle((10, 90, 110, 160), outline=(255,255,0), fill=(255,0,255))

def Ex( surface ) :
  # Draw a white X.
  surface.line((10, 170, 110, 230), fill=(255,255,255))
  surface.line((10, 230, 110, 170), fill=(255,255,255))

def Triangle( surface ) :
  # Draw a cyan triangle with a black outline.
  surface.polygon([(10, 275), (110, 240), (110, 310)], outline=(0,0,0), fill=(0,255,255))

def Text( tft ) :
  s = tft.surface

  # Load default font.
  font = ImageFont.load_default()

  # Alternatively load a TTF font.
  # Some other nice fonts to try: http://www.dafont.com/bitmap.php
  #font = ImageFont.truetype('Minecraftia.ttf', 16)

  # Define a function to create rotated text.  Unfortunately PIL doesn't have good
  # native support for rotated fonts, but this function can be used to make a
  # text image and rotate it so it's easy to paste in the buffer.
  def draw_rotated_text(image, text, position, angle, font, fill=(255,255,255)):
    # Get rendered font width and height.
    draw = ImageDraw.Draw(image)
    width, height = draw.textsize(text, font=font)
    # Create a new image with transparent background to store the text.
    textimage = Image.new('RGBA', (width, height), (0,0,0,0))
    # Render the text.
    textdraw = ImageDraw.Draw(textimage)
    textdraw.text((0,0), text, font=font, fill=fill)
    # Rotate the text image.
    rotated = textimage.rotate(angle, expand=1)
    # Paste the text into the image, using it as a mask for transparency.
    image.paste(rotated, position, rotated)

  # Write two lines of white text on the buffer, rotated 90 degrees counter clockwise.
  draw_rotated_text(tft.buffer, 'Hello World!', (150, 120), 90, font, fill=(255,255,255))
  draw_rotated_text(tft.buffer, 'This is a line of text.', (170, 90), 90, font, fill=(255,255,255))

