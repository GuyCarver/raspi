
from oled import *
import time
from urllib.request import urlopen
from json import loads
from threading import Thread
import settings

class Clock:

  #x,y,dir (0=right, 1=down)
  #  0
  #1   2
  #  3
  #4   5
  #  6
  segs = [(0,0,0), (0,0,1), (1,0,1), (0,1,0), (0,1,1), (1,1,1), (0,2,0),
          (1,0,0), (2,0,1), (1,1,0), (2,1,1), (2,2,0)]
  segadjust = 2 #pixels to adjust segment draw position by.

  nums = [[0,1,2,4,5,6], [2,5], [0,2,3,4,6], [0,2,3,5,6], [1,2,3,5],
          [0,1,3,5,6], [0,1,3,4,5,6], [0,2,5], [0,1,2,3,4,5,6], [0,1,2,3,5]]

  #apm and deg symbol
  apm = [(0,1,2,3,4,5), (0,1,2,3,4), (0,1,2,4,5,7,8,10), (0,1,2,3)]

  digitpos = [0.0, 1.3, 3.1, 4.4, 6.0]
  twoline = 7     #minimum size for 2 line width of segment.
  threeline = 10  #minimum size for 3 line width of segment.
  tempsize = 6    #Size in pixels of temp half segment.

  defaulttempinterval = 30    #seconds to wait before tempurature update.
  defaulttempdur = 3          #Duration of main temp display.
  defaulttempupdate = 60 * 5  #Time between tempurature querries.

  def __init__( self ) :
    #Frederick = 2458710
    #Rockville = 2483553
    self._tempdisplayinterval = Clock.defaulttempinterval
    self.tempdisplaytime = Clock.defaulttempdur
    self.tempupdateinterval = Clock.defaulttempupdate
    self.wh = 15  #Size of half of the segment (0-3).  IE: 6 is drawn at 30 if wh is 15.
    self.x = 5.0
    self.y = 10.0
    self.size = (128, 64)
    self.i2c = oled()
    self.digits = (0, 0, 0, 0, 0, 0)
    self.temp = 0
    self.text = 'Sunny'
    self._url = ''
    self.location = 2458710

    self._ldthread = Thread(target=self.loadthread)
    self._ldthread.start()
    self._settingsthread = Thread(target=self.startsettings)
    self._settingsthread.start()

  @property
  def tempdisplayinterval( self ) :
    return self._tempdisplayinterval

  @tempdisplayinterval.setter
  def tempdisplayinterval( self, aValue ) :
    self._tempdisplayinterval = min(aValue, 60 - self.tempdisplaytime)

  @property
  def tempdisplaytime( self ) :
    return self._tempdisplaytime

  @tempdisplaytime.setter
  def tempdisplaytime( self, aValue ) :
    self._tempdisplaytime = aValue
    self.tempdisplayinterval = self.tempdisplayinterval

  @property
  def tempupdateinterval( self ) :
    return self._tempupdateinterval

  @tempupdateinterval.setter
  def tempupdateinterval( self, aValue ) :
    self._tempupdateinterval = aValue

  @property
  def location( self ) :
    return self._location

  @location.setter
  def location( self, aLoc ) :
    self._location = aLoc
    self._url = 'https://query.yahooapis.com/v1/public/yql?q=select%20item.condition%20from%20weather.forecast%20where%20woeid%3D' + str(aLoc) + '&format=json'

  def startsettings( self ) :
    settings.run(self)

  def loadthread( self ) :
    while True:
      self.UpdateWeather()
      time.sleep(self.tempupdateinterval)

  def iline( self, sx, sy, ex, ey ) :
    self.i2c.line((int(sx), int(sy)), (int(ex), int(ey)), 1)

  def drawseg( self, pos, seg, wh ) :
    x,y,d = seg
    x = x * wh + pos[0]
    y = y * wh + pos[1]
    if d == 0:
      sx = x + Clock.segadjust
      ex = sx + wh - Clock.segadjust
      self.iline(sx, y+1, ex, y+1)
      sx += 1
      ex -= 1
      if wh >= Clock.twoline:
        self.iline(sx,y,ex,y)
      if wh >= Clock.threeline :
        self.iline(sx,y+2,ex,y+2)
    else:
      sy = y + 1
      ey = sy + wh - 1
      self.iline(x+1, sy, x+1, ey)
      sy += 1
      ey -= 1
      if wh >= Clock.twoline:
        self.iline(x,sy,x,ey)
      if wh >= Clock.threeline :
        self.iline(x+2,sy,x+2,ey)

  def drawsegs( self, pos, seglist, wh ) :
    for s in seglist:
      self.drawseg(pos, Clock.segs[s], wh)

  def draw( self ) :
    self.i2c.clear()
    x = int(self.x)
    y = int(self.y)

    def drawdig( anum ) :
      p =  (x + (self.wh * Clock.digitpos[anum]), y)
      self.drawsegs(p, Clock.nums[self.digits[anum]], self.wh )

    def drawapm( anum ) :
      wh = self.wh // 2
      p = (x + (self.wh * Clock.digitpos[anum]), y)
      d = self.digits[anum]
      self.drawsegs(p, Clock.apm[d], wh)
      if d < 2:
        p = (p[0] + wh + (wh // 2) + 1, y)
        self.drawsegs(p, Clock.apm[2], wh)

    drawdig(0)
    drawdig(1)
    drawdig(2)
    drawdig(3)
    drawapm(4)

    p = (x + (self.wh * Clock.digitpos[4]), y + 3 + (self.wh * 2))
    wh = Clock.tempsize
    n1 = (self.temp // 10) % 10
    n2 = self.temp % 10
    self.drawsegs(p, Clock.nums[n1], wh)
    p = (p[0] + wh + 2, p[1])
    self.drawsegs(p, Clock.nums[n2], wh)
    p = (p[0] + wh + 4, p[1])
    self.drawsegs(p, Clock.apm[3], wh)

    def drawrect( pos ) :
      self.i2c.fillrect(pos, (3,3), 1)

    if (self.digits[5] & 1) == 1:
      sx = (Clock.digitpos[1] + 1.0 + Clock.digitpos[2]) / 2
      sy = (self.wh // 3) * 2
      p = (int((sx * self.wh) + self.x), int(self.y + sy))
      drawrect(p)
      sy += sy
      p = (p[0], int(self.y + sy))
      drawrect(p)

    self.i2c.display()

  def UpdateWeather( self ) :
    try:
      req = urlopen(self._url, None, 2)
      d = req.read()
      j = loads(d.decode('utf-8'))
      cond = j['query']['results']['channel']['item']['condition']
      self.temp = int(cond['temp'])
      self.text = cond['text']
    except Exception as e:
      pass

    self.tempset = True #Set to true if succeeded or not.  We only try once.

  def Update( self ) :
    t = time.localtime()
    h = t.tm_hour
    m = t.tm_min
    s = t.tm_sec
    apm = 0
    if h >= 12:
      apm = 1
      if h > 12:
        h -= 12

    #display temp in main display if it's time.
    if (s % self.tempdisplayinterval) < self.tempdisplaytime:
      h = 0
      m = self.temp
      apm = 3
    self.digits = (h // 10, h % 10, m // 10, m % 10, apm, s)

  def run( self ) :
    runit = True
    while runit:
      self.Update()
      self.draw()
      time.sleep(0.2)

def run(  ) :
  c = Clock()
  c.run()

if __name__ == '__main__':
  run()
