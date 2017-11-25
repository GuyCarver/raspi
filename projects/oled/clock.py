#oled display of clock with temperature.
#also web hosted settings IE: 192.168.2.62 in a browser will pull up the settings page.
#This module must be run under sudo or the settings server will fail from permission exception.

import os, sys
from oled import *
import time, datetime
from urllib.request import urlopen
from json import loads, dump, load
from threading import Thread, Lock
import checkface
import settings

#todo: camera controls for gain, saturation, contrast, brightness, exposure.

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
  tmconvert = '{:02d}:{:02d}'
  dtconvert = '{}-{:02d}-{:02d}'
  colorconvert = '#{:06x}'
  savename = 'clock.json'

  defaulttempinterval = 30    #seconds to wait before tempurature update.
  defaulttempdur = 3          #Duration of main temp display.
  defaulttempupdate = 5.0     #Time between tempurature querries.
  defaultdisplaydur = 5.0     #Default time in seconds display stays on after face detection.

  def __init__( self ) :
    self._onlock = Lock()
    self._tempdisplayinterval = Clock.defaulttempinterval
    #set properties
    self.tempdisplaytime = Clock.defaulttempdur
    self.tempupdateinterval = Clock.defaulttempupdate
    self.displayduration = Clock.defaultdisplaydur
    self.wh = 15  #Size of half of the segment (0-3).  IE: 6 is drawn at 30 if wh is 15.
    self.pos = (5, 10)
    self.size = (128, 64)
    self.i2c = oled(0)
    self.digits = (0, 0, 0, 0, 0, 0)
    self._tempdisplay = True
    self._h = 0
    self._m = 0
    self.temp = 0
    self.text = 'Sunny'
    self._color = 0x00FFFF
    self._url = ''
    self.location = '2458710'   #Rockville = 2483553, Frederick = 2458710
    self.load()
    self._running = True
    self._ontime = 0.0
    self.on = True
    self._dirtydisplay = False
    self._prevtime = time.time()
    self._checker = checkface.Create();
    checkface.SetHorizontalFlip(self._checker, True)
#    checkface.SetBrightness(self._checker, 20.0)

    self._sthread = Thread(target=self.seethread)
    self._sthread.start()

    self._ldthread = Thread(target=self.loadthread)
    self._ldthread.start()

    self._settingsthread = Thread(target=self.startsettings)
    self._settingsthread.start()

  @property
  def on( self ) :
    return self._ontime > 0.0

  @on.setter
  def on( self, aTF ) :
    self._onlock.acquire()
    self._ontime = self.displayduration if aTF else 0.0
    self._onlock.release()

  @property
  def tempdisplay( self ) :
    return self._tempdisplay

  @tempdisplay.setter
  def tempdisplay( self, aValue ) :
    self._tempdisplay = aValue

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
    self.tempdisplayinterval = self.tempdisplayinterval #Recalculate the temp display interval.

  @property
  def tempupdateinterval( self ) :
    return self._tempupdateinterval

  @tempupdateinterval.setter
  def tempupdateinterval( self, aValue ) :
    self._tempupdateinterval = aValue

  @property
  def displayduration( self ) :
    return self._displayduration

  @displayduration.setter
  def displayduration( self, aValue ) :
    self._displayduration = aValue

  @property
  def hhmm( self ) :
    return Clock.tmconvert.format(self._h, self._m)

  @hhmm.setter
  def hhmm( self, aValue ) :
    #todo: Convert 'hh:mm' into hours/minutes and set the time.
    pass

  @property
  def date( self ) :
    t = datetime.date.today()
    return Clock.dtconvert.format(t.year, t.month, t.day)

  @property
  def color( self ) :
    return self._color

  @color.setter
  def color( self, aValue ) :
    self._color = aValue

  @property
  def colorstr( self ) :
    return Clock.colorconvert.format(self._color)

  @colorstr.setter
  def colorstr( self, aValue ) :
    c = int(aValue[1:], 16) #skin the leading #
    self._color = c

  @property
  def location( self ) :
    return self._location

  @location.setter
  def location( self, aLoc ) :
    self._location = aLoc
    self._url = 'https://query.yahooapis.com/v1/public/yql?q=select%20item.condition%20from%20weather.forecast%20where%20woeid%3D' + str(aLoc) + '&format=json'

  def startsettings( self ) :
#    print("Starting settings server")
    settings.run(self)

  def seethread( self ) :
    c = 0
    while self._running:
      elapse = time.time()
      #todo: Look for faces.  If found set on.
      #for now we just trigger every 15 seconds for 1 second.
#      print("checking for face {}".format(c))
      c += 1
      if checkface.Check(self._checker) :
#      if (int(elapse) % 15) == 0 :
        print("  face found!")
        self.on = True

      delay = 2.0 - (time.time() - elapse)
      #only delay if time left to delay for.
      if delay > 0.0 :
        time.sleep(delay)

  def loadthread(self):
    while self._running:
      self.UpdateWeather()
      elapse = self.tempupdateinterval
      while (elapse > 0.0) and self._running:
        elapse -= 1.0
        time.sleep(1.0)

  def save( self ) :
      with open(Clock.savename, 'w+') as f:
        data = {}
        data['tempon'] = self.tempdisplay
        data['duration'] = self.displayduration
        data['tempduration'] = self.tempdisplaytime
        data['interval'] = self.tempdisplayinterval
        data['update'] = self.tempupdateinterval
        data['location'] = self.location
        data['color'] = self.colorstr

        dump(data, f)

  def load( self ) :
    try:
      with open(Clock.savename, 'r') as f:
        data = load(f)
        self.tempdisplay = data['tempon']
        self.tempdisplayinterval = data['interval']
        self.displayduration = data['duration']
        self.tempdisplaytime = data['tempduration']
        self.tempupdateinterval = data['update']
        self.location = data['location']
        self.colorstr = data['color']
    except:
      pass

  def iline( self, sx, sy, ex, ey ) :
    self._dirtydisplay = True
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
    if self.on :
      self.i2c.clear()
      x, y = self.pos

      #Draw an hour or minute digit.
      def drawdig( anum ) :
        p = (x + int(self.wh * Clock.digitpos[anum]), y)
        self.drawsegs(p, Clock.nums[self.digits[anum]], self.wh )

      #Draw am or pm depending on the hour.
      def drawapm( anum ) :
        wh = self.wh // 2
        p = (x + int(self.wh * Clock.digitpos[anum]), y)
        d = self.digits[anum]
        self.drawsegs(p, Clock.apm[d], wh)
        if d < 2:
          p = (p[0] + wh + (wh // 2) + 1, y)
          self.drawsegs(p, Clock.apm[2], wh)

      #Fraw the hh mm and am/pm.
      drawdig(0)
      drawdig(1)
      drawdig(2)
      drawdig(3)
      drawapm(4)

      #If we want to display the temperature then do so at the bottom right.
      if self.tempdisplay :
        p = (x + int(self.wh * Clock.digitpos[4]), y + 3 + (self.wh * 2))
        wh = Clock.tempsize
        n1 = (self.temp // 10) % 10
        n2 = self.temp % 10
        self.drawsegs(p, Clock.nums[n1], wh)
        p = (p[0] + wh + 2, p[1])
        self.drawsegs(p, Clock.nums[n2], wh)
        p = (p[0] + wh + 4, p[1])
        self.drawsegs(p, Clock.apm[3], wh)

      #Fill a 3x3 rectangle at the given position.  Used to draw colon.
      def drawrect( pos ) :
        self.i2c.fillrect(pos, (3,3), 1)

      #Draw the colon in between hh and mm every second for a second.
      if (self.digits[5] & 1) == 1:
        sx = (Clock.digitpos[1] + 1.0 + Clock.digitpos[2]) / 2
        sy = (self.wh // 3) * 2
        p = (int(sx * self.wh) + x, y + sy)
        drawrect(p)
        sy += sy
        p = (p[0], y + sy)
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
      print(e)

  def Update( self ) :
    ct = time.time()
    dt = min(1.0, ct - self._prevtime) #clamp max elapsed time to 1 second.
    self._prevtime = ct

    t = time.localtime()
    h = t.tm_hour
    m = t.tm_min
    s = t.tm_sec
    self._h = h
    self._m = m

    apm = 0
    #display temp in main display if it's time.
    if self.tempdisplay and ((s % self.tempdisplayinterval) < self.tempdisplaytime) :
      h = 0
      m = self.temp
      apm = 3
    elif h >= 12:
      apm = 1
      if h > 12:
        h -= 12

    self.digits = (h // 10, h % 10, m // 10, m % 10, apm, s)

    if self.on :
      self._onlock.acquire()
      self._ontime -= dt
      rem = self._ontime
      self._onlock.release()

      #if time's up then clear the display.
      if rem <= 0 :
        self.i2c.clear()
        self.i2c.display()

  def run( self ) :
    try:
      while self._running:
        elapsed = time.time()
        self.Update()
        self.draw()
        delay = 0.2 - (time.time() - elapsed)
        if delay > 0.0 :
          time.sleep(delay)
    except KeyboardInterrupt:
      print("ctrl-c exit.")
      self._running = False

    self.save()                                 #Save current settings.
    self._sthread.join()
    self._ldthread.join()
    self._settingsthread.join()

def run(  ) :
    c = Clock()
    c.run()

run()
