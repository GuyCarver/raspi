#driver for Sainsmart 1.8" TFT display ST7735
#Translated by Guy Carver from the ST7735 sample code.

#NOTE: This current code will set the pixel at 0,0 but the scrolling will not scroll it.  Don't know if it's software causing it or not.

from smbus import SMBus

#Buffer layout in bits.  128 columns by 64 rows.
#Each byte represents 8 pixels in a row.
#   Column
# R 0   8   10 ... 3F8
# O 1   9   11 ... 3F9
# W 2   A   12 ... 3FA
#   3   B   13 ... 3FB
#   4   C   14 ... 3FC
#   5   D   15 ... 3FD
#   6   E   16 ... 3FE
#   7   F   17 ... 3FF
#   400 408
#   401 409
#   402 40A
#   403 40B
#   404 40C
#   405 40D
#   406 40E
#   407 40F

class oled(object) :
  """diyMall OLED 9.6 128x64 pixel display driver."""

  ADDRESS = 0x3C  # 011110+SA0+RW - 0x3C or 0x3D
  STOP = 0
  LEFT = 1
  RIGHT = 2
  DIAGLEFT = 3
  DIAGRIGHT = 4

  _CMDMODE = 0x00
  _DATAMODE = 0x40

  _SETCONTRAST = 0x81
  _DISPLAYALLON_RESUME = 0xA4
  _DISPLAYALLON = 0xA5
  _NORMALDISPLAY = 0xA6
  _INVERTDISPLAY = 0xA7
  _DISPLAYOFF = 0xAE
  _DISPLAYON = 0xAF

  _SETDISPLAYOFFSET = 0xD3
  _SETCOMPINS = 0xDA

  _SETVCOMDETECT = 0xDB

  _SETDISPLAYCLOCKDIV = 0xD5
  _SETPRECHARGE = 0xD9

  _SETMULTIPLEX = 0xA8

  _SETLOWCOLUMN = 0x00
  _SETHIGHCOLUMN = 0x10

  _SETSTARTLINE = 0x40

  _MEMORYMODE = 0x20

  _COMSCANINC = 0xC0
  _COMSCANDEC = 0xC8

  _SEGREMAP = 0xA0

  _CHARGEPUMP = 0x8D

  _EXTRNALVCC = 0x1
  _SWITCHAPVCC = 0x2

  _ACTIVATE_SCROLL = 0x2F
  _DEACTIVATE_SCROLL = 0x2E
  _SET_VERTICAL_SCROLL_AREA = 0xA3
  _RIGHT_HORIZONTAL_SCROLL = 0x26
  _LEFT_HORIZONTAL_SCROLL = 0x27
  _VERTICAL_AND_RIGHT_HORIZONTAL_SCROLL = 0x29
  _VERTICAL_AND_LEFT_HORIZONTAL_SCROLL = 0x2A

  def __init__( self, aLoc=1 ) :
    """aLoc I2C pin location is either 1 for 'X' or 2 for 'Y'."""
    self._size = (128, 64)
    self._rotation = 0
    self._inverted = False
    self._on = False
    self.i2c = SMBus(aLoc)
    self.pages = self.size[1] // 8
    self.bytes = self.size[0] * self.pages
    self.buffer = bytearray(self.bytes)

    #Send the initialization commands.
    self._command(oled._DISPLAYOFF,
      oled._SETDISPLAYCLOCKDIV, 0x80, #suggested ratio.
      oled._SETMULTIPLEX, 0x3F,
      oled._SETDISPLAYOFFSET, 0x0,
      oled._SETSTARTLINE, #| 0x0
      oled._CHARGEPUMP, 0x14,  #No external power.
      oled._MEMORYMODE, 0x00,  #Act like ks0108
      oled._SEGREMAP + 0x01,
      oled._COMSCANDEC,
      oled._SETCOMPINS, 0x12,
      oled._SETCONTRAST, 0xCF,
      oled._SETPRECHARGE, 0xF1,
      oled._SETVCOMDETECT, 0x40,
      oled._DISPLAYALLON_RESUME,
      oled._NORMALDISPLAY, 0XB0, 0x10, 0x01) #Set original position to 0,0.

    self.on = True

    self.display()

  @property
  def size( self ) : return self._size

  @property
  def rotation( self ) : return self._rotation

  @rotation.setter
  def rotation( self, aValue ) :
    self._rotation = aValue & 3

  @property
  def on( self ) : return self._on

  @on.setter
  def on( self, aTF ) :
    if aTF != self._on :
      self._on = aTF
      '''Turn display on or off.'''
      self._command(oled._DISPLAYON if aTF else oled._DISPLAYOFF)

  @property
  def invert( self ) : return self._inverted

  @invert.setter
  def invert( self, aTF ) :
    if aTF != self._inverted :
      self._inverted = aTF
      self._command(oled._INVERTDISPLAY if aTF else oled._NORMALDISPLAY)

  def _data( self, aValue ) :
    '''
    Sends a data byte or sequence of data bytes through to the
    device - maximum allowed in one transaction is 32 bytes, so if
    data is larger than this it is sent in chunks.
    In our library, only data operation used is 128x64 long, ie whole canvas.
    '''

    for i in range(0, len(aValue), 32):
      self.i2c.write_i2c_block_data(oled.ADDRESS, oled._DATAMODE, list(aValue[i:i+32]))

  def _command( self, *aValue ) :
    assert(len(aValue) <= 32)
    self.i2c.write_i2c_block_data(oled.ADDRESS, oled._CMDMODE, list(aValue))

  def fill( self, aValue ) :
    for x in range(0, self.bytes):
      self.buffer[x] = aValue;

  def clear( self ) :
    self.fill(0)

  def pixel( self, aPos, aOn ) :
    '''Draw a pixel at the given position'''
    x, y = aPos
    w, h = self.size
    if 0 <= x < w and 0 <= y < h:
      if self._rotation == 1:
        aPos = (w - y - 1, x)
      elif self._rotation == 2:
        aPos = (w - x - 1, h - y - 1)
      elif self._rotation == 3:
        aPos = (y, h - x - 1)

      bit = 1 << (aPos[1] % 8)
      index = (aPos[0] + (aPos[1] // 8) * w)

      if aOn :
        self.buffer[index] |= bit
      else :
        self.buffer[index] &= ~bit

  def line( self, aStart, aEnd, aOn ) :
    '''Draws a line from aStart to aEnd in the given color.  Vertical or horizontal
       lines are forwarded to vline and hline.'''
    px, py = aStart
    ex, ey = aEnd
    dx = int(ex - px)
    dy = int(ey - py)
    inx = 1 if dx > 0 else -1
    iny = 1 if dy > 0 else -1

    dx = abs(dx)
    dy = abs(dy)
    if (dx >= dy):
      dy <<= 1
      e = dy - dx
      dx <<= 1
      while (px != ex):
        self.pixel((px, py), aOn)
        if (e >= 0):
          py += iny
          e -= dx
        e += dy
        px += inx
    else:
      dx <<= 1
      e = dx - dy
      dy <<= 1
      while (py != ey):
        self.pixel((px, py), aOn)
        if (e >= 0):
          px += inx
          e -= dy
        e += dx
        py += iny

  def fillrect( self, aStart, aSize, aOn ) :
    '''Draw a filled rectangle.  aStart is the smallest coordinate corner
       and aSize is a tuple indicating width, height.'''
    x, y = aStart
    w, h = aSize
    ex = x + w
#    print("{}, {}, {}, {}".format(type(x), type(y), type(w), type(h)))
    for i in range(y, y + h):
      self.line((x, i), (ex, i), aOn)

  def text( self, aPos, aString, aColor, aFont, aSize = 1 ) :
    '''Draw a text at the given position.  If the string reaches the end of the
       display it is wrapped to aPos[0] on the next line.  aSize may be an integer
       which will size the font uniformly on w,h or a or any type that may be
       indexed with [0] or [1].'''

    if aFont == None:
      return

    #Make a size either from single value or 2 elements.
    if (type(aSize) == int) or (type(aSize) == float):
      wh = (aSize, aSize)
    else:
      wh = aSize

    px, py = aPos
    width = wh[0] * aFont["Width"] + 1
    for c in aString:
      self.char((px, py), c, aColor, aFont, wh)
      px += width
      #We check > rather than >= to let the right (blank) edge of the
      # character print off the right of the screen.
      if px + width > self._size[0]:
        py += aFont["Height"] * wh[1] + 1
        px = aPos[0]

  def char( self, aPos, aChar, aOn, aFont, aSizes ) :
    '''Draw a character at the given position using the given font and color.
       aSizes is a tuple with x, y as integer scales indicating the
       # of pixels to draw for each pixel in the character.'''

    if aFont == None:
      return

    startchar = aFont['Start']
    endchar = aFont['End']

    ci = ord(aChar)
    if (startchar <= ci <= endchar):
      fontw = aFont['Width']
      fonth = aFont['Height']
      ci = (ci - startchar) * fontw

      charA = aFont["Data"][ci:ci + fontw]
      px = aPos[0]
      if aSizes[0] <= 1 and aSizes[1] <= 1 :
        for c in charA :
          py = aPos[1]
          for r in range(fonth) :
            if c & 0x01 :
              self.pixel((px, py), aOn)
            py += 1
            c >>= 1
          px += 1
      else:
        for c in charA :
          py = aPos[1]
          for r in range(fonth) :
            if c & 0x01 :
              self.fillrect((px, py), aSizes, aOn)
            py += aSizes[1]
            c >>= 1
          px += aSizes[0]

  def _scrollLR( self, start, stop, aDir ) :
    self._command(aDir, 0x00, start, 0x00, stop, 0x00, 0xFF, oled._ACTIVATE_SCROLL)

  def _scrollDiag( self, start, stop, aDir ) :
    self._command(oled._SET_VERTICAL_SCROLL_AREA, 0x00, self.size()[1], aDir, 0x00,
      start, 0x00, stop, 0x01, oled._ACTIVATE_SCROLL)

  def scroll( self, adir, start=0, stop=7 ) :
    '''Scroll in given direction.  Display is split in 8 vertical segments.'''
    if adir == oled.STOP :
      self._command(oled._DEACTIVATE_SCROLL)
    elif adir == oled.LEFT :
      self._scrollLR(start, stop, oled._LEFT_HORIZONTAL_SCROLL)
    elif adir == oled.RIGHT :
      self._scrollLR(start, stop, oled._RIGHT_HORIZONTAL_SCROLL)
    elif adir == oled.DIAGLEFT :
      self._scrollDiag(start, stop, oled._VERTICAL_AND_LEFT_HORIZONTAL_SCROLL)
    elif adir == oled.DIAGRIGHT :
      self._scrollDiag(start, stop, oled._VERTICAL_AND_RIGHT_HORIZONTAL_SCROLL)

  def display( self ) :
    self._command(oled._SETLOWCOLUMN, oled._SETHIGHCOLUMN, oled._SETSTARTLINE)
    self._data(self.buffer)


