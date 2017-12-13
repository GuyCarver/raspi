#!/usr/bin/env python3
#oled display of clock with temperature.
#Display on/off is controlled by face detection.
#also web hosted settings IE: 192.168.2.62 in a browser will pull up the settings page.
#This module must be run under sudo or the settings server will fail from permission exception.

import os, sys
import RPi.GPIO as GPIO
from oled import *
import time, datetime
from urllib.request import urlopen
from json import loads, dump, load
from threading import Thread #,Lock
import keyboard
import checkface
import settings

#done: Need to speed up the checkface system.  It takes way too long at the moment.  May need to go with a better raspi.
# switched to haarcascade_frontalface_default.xml and reduced image scale to .25 and this sped things up as well as improved accuracy.
#done: Try checkface from the main thread to see if it's more efficient.  It's messing with display at the moment.
#  Did this and it definitely worked better so I'm staying with it.

class Clock:

  #x,y,dir x,y are mulipliers. Dir = (0=right, 1=down)
  #  0
  #1   2
  #  3
  #4   5
  #  6
  segs = [(0,0,0), (0,0,1), (1,0,1), (0,1,0), (0,1,1), (1,1,1), (0,2,0),
          (1,0,0), (2,0,1), (1,1,0), (2,1,1), (2,2,0)]
  segadjust = 2 #pixels to adjust segment draw position by to simulate a segment display.

  #Lists of segments needed to display 0-9.
  nums = [[0,1,2,4,5,6], [2,5], [0,2,3,4,6], [0,2,3,5,6], [1,2,3,5],
          [0,1,3,5,6], [0,1,3,4,5,6], [0,2,5], [0,1,2,3,4,5,6], [0,1,2,3,5]]

  #apm and deg symbol
  apm = [(0,1,2,3,4,5), (0,1,2,3,4), (0,1,2,4,5,7,8,10), (0,1,2,3)]

  #Position x mulipliers of the clock digits and am/pm.
  digitpos = [0.0, 1.3, 3.1, 4.4, 6.0]
  twoline = 7     #minimum size for 2 line width of segment.
  threeline = 10  #minimum size for 3 line width of segment.
  tempsize = 6    #Size in pixels of temp half segment.
  tmconvert = '{:02d}:{:02d}'
  dtconvert = '{}-{:02d}-{:02d}'
  colorconvert = '#{:06x}'
  savename = '/home/pi/projects/oled/clock.json'

  defaulttempinterval = 30    #seconds to wait before tempurature update.
  defaulttempdur = 3          #Duration of main temp display.
  defaulttempupdate = 5.0     #Time between tempurature querries.
  defaultdisplaydur = 5.0     #Default time in seconds display stays on after face detection.
  defaultfacecheck = 2.0      #Check for face every n seconds.
  ledcontrolpin = 24           #GPIO24 pin controls IR LEDs.

  def __init__( self ) :
    print("Init")
    #Put the lock stuff in if running face detection in bg thread.
#    self._onlock = Lock()
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(Clock.ledcontrolpin, GPIO.OUT)
    self._tempdisplayinterval = Clock.defaulttempinterval
    #set properties
    self.tempdisplaytime = Clock.defaulttempdur
    self.tempupdateinterval = Clock.defaulttempupdate
    self.displayduration = Clock.defaultdisplaydur
    self.wh = 15  #Size of half of the segment (0-3).  IE: segment 6 is drawn at y of 30 if wh is 15.
    self.pos = (5, 10)
    self.size = (128, 64)
    try:
      self._oled = oled(1)  #1st try later versions of the pi.
    except:
      self._oled = oled(0)  #if those fail we're using the 1st gen maybe?

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
    self._checktime = Clock.defaultfacecheck
    try:
      print("creating clock.")
      self._checker = checkface.Create()
    except:
      print("Error with clock.")

    self._iron = False
    self.vflip = True
    self.contrast = 75.0
    self.saturation = 100.0

    print("testing for keyboard")
    #If no keyboard we'll get an exception here so turn off keyboard flag.
    try:
      bres = keyboard.is_pressed('q')
      self._haskeyboard = True
    except:
      self._haskeyboard = False

#This is the system to look for face in the bg thread.  Don't need it though.
#    self._sthread = Thread(target=self.seethread)
#    self._sthread.start()

    print("starting threads.")
    self._wtthread = Thread(target=self.weatherthread)

    self._settingsthread = Thread(target=self.startsettings)

  def __del__( self ) :
    self.iron = False

  @property
  def iron( self ) :
    '''Return true if IR LEDs are currently on.'''
    return self._iron

  @iron.setter
  def iron( self, aTF ) :
    '''Set IR LEDs on/off.'''
    self._iron = aTF
    GPIO.output(Clock.ledcontrolpin, GPIO.HIGH if aTF else GPIO.LOW)

  @property
  def on( self ) :
    '''Return true if display is currently on.'''
    return self._ontime > 0.0

  @on.setter
  def on( self, aTF ) :
    '''Set display time to displayduration if on or 0 if off.'''
#    self._onlock.acquire()
    self._ontime = self.displayduration if aTF else 0.0
#    self._onlock.release()

  @property
  def tempdisplay( self ) :
    '''Return if large temp display is enabled.'''
    return self._tempdisplay

  @tempdisplay.setter
  def tempdisplay( self, aValue ) :
    '''Enable/Disable large temperature display.'''
    self._tempdisplay = aValue

  @property
  def tempdisplayinterval( self ) :
    '''Get the interval in second for temperature display trigger.'''
    return self._tempdisplayinterval

  @tempdisplayinterval.setter
  def tempdisplayinterval( self, aValue ) :
    '''Set the interval in second for temperature display trigger.  Clamped to 60-tempdisplaytime.'''
    self._tempdisplayinterval = min(aValue, 60 - self.tempdisplaytime)

  @property
  def tempdisplaytime( self ) :
    '''Get the temperature display duration.'''
    return self._tempdisplaytime

  @tempdisplaytime.setter
  def tempdisplaytime( self, aValue ) :
    '''Set the temperature display duration and recalculate tempdisplayinterval.'''
    self._tempdisplaytime = aValue
    self.tempdisplayinterval = self.tempdisplayinterval #Recalculate the temp display interval.

  @property
  def tempupdateinterval( self ) :
    '''Get the temperature update interval in minutes.'''
    return self._tempupdateinterval

  @tempupdateinterval.setter
  def tempupdateinterval( self, aValue ) :
    '''Set the temperature update interval in minutes.'''
    self._tempupdateinterval = aValue

  @property
  def displayduration( self ) :
    '''Get duration of the display after turned on.'''
    return self._displayduration

  @displayduration.setter
  def displayduration( self, aValue ) :
    '''Set duration of the display after turned on.'''
    self._displayduration = aValue

  @property
  def hhmm( self ) :
    '''Get "hh:mm" in string format (for the settings http server).'''
    return Clock.tmconvert.format(self._h, self._m)

  @hhmm.setter
  def hhmm( self, aValue ) :
    '''todo: Convert "hh:mm" into hours/minutes and set the time.'''
    pass

  @property
  def date( self ) :
    '''Get "yy-mm-dd" in string format (for the settings http server).'''
    t = datetime.date.today()
    return Clock.dtconvert.format(t.year, t.month, t.day)

  @date.setter
  def date( self, aValue ) :
    '''todo: Convert "yy-mm-dd" into year, month, day and set the date.'''
    pass

  @property
  def color( self ) :
    '''Get the color in 0x00RRGGBB'''
    return self._color

  @color.setter
  def color( self, aValue ) :
    '''Set the color'''
    self._color = aValue

  @property
  def colorstr( self ) :
    '''Get the color as a string "#RRGGBB".'''
    return Clock.colorconvert.format(self._color)

  @colorstr.setter
  def colorstr( self, aValue ) :
    '''Set the color from a string format "#RRGGBB".'''
    c = int(aValue[1:], 16) #skin the leading # and convert base 16 digits to int.
    self._color = c

  @property
  def location( self ) :
    '''Get the location WOEID.'''
    return self._location

  @location.setter
  def location( self, aLoc ) :
    '''Set the location WOEID and setup the querry url for the weather update thread.'''
    self._location = aLoc
    self._url = 'https://query.yahooapis.com/v1/public/yql?q=select%20item.condition%20from%20weather.forecast%20where%20woeid%3D' + str(aLoc) + '&format=json'

#Camera properties.
  @property
  def vflip( self ) :
    '''Get camera vertical flip state.'''
    return self._vflip

  @vflip.setter
  def vflip( self, aValue ) :
    '''Set camera virtical flip state.'''
    self._vflip = aValue
    checkface.SetVerticalFlip(self._checker, aValue)

  @property
  def brightness( self ) :
    '''Get camera brightness 0.0-100.0.'''
    return checkface.GetProp(self._checker, checkface.CV_CAP_PROP_BRIGHTNESS)

  @brightness.setter
  def brightness( self, aValue ) :
    '''Set camera brightness 0.0-100.0.'''
    checkface.SetProp(self._checker, checkface.CV_CAP_PROP_BRIGHTNESS, aValue)

  @property
  def contrast( self ) :
    '''Get camera contrast 0.0-100.0.'''
    return checkface.GetProp(self._checker, checkface.CV_CAP_PROP_CONTRAST)

  @contrast.setter
  def contrast( self, aValue ) :
    '''Set camera contrast 0.0-100.0.'''
    checkface.SetProp(self._checker, checkface.CV_CAP_PROP_CONTRAST, aValue)

  @property
  def saturation( self ) :
    '''Get camera saturation 0.0-100.0.'''
    return checkface.GetProp(self._checker, checkface.CV_CAP_PROP_SATURATION)

  @saturation.setter
  def saturation( self, aValue ) :
    '''Set camera saturation 0.0-100.0.'''
    checkface.SetProp(self._checker, checkface.CV_CAP_PROP_SATURATION, aValue)

  @property
  def gain( self ) :
    '''Get camera gain 0.0-100.0.'''
    return checkface.GetProp(self._checker, checkface.CV_CAP_PROP_GAIN)

  @gain.setter
  def gain( self, aValue ) :
    '''Set camera gain 0.0-100.0.'''
    checkface.SetProp(self._checker, checkface.CV_CAP_PROP_GAIN, aValue)

  @property
  def exposure( self ) :
    '''Get camera exposure -1.0-100.0.'''
    return checkface.GetProp(self._checker, checkface.CV_CAP_PROP_EXPOSURE)

  @exposure.setter
  def exposure( self, aValue ) :
    '''Set camera brightness -1.0-100.0. -1.0 equals automatic.'''
    checkface.SetProp(self._checker, checkface.CV_CAP_PROP_EXPOSURE, aValue)

#END Camera properties.

  def startsettings( self ) :
#    print("Starting settings server")
    settings.run(self)

  def seethread( self ) :
    '''Not currently used.  Run checkface in the background.'''
    while self._running:
#      elapse = time.time()
      if checkface.Check(self._checker) :
        print("  face found!")
        self.on = True

      #delay for n seconds - time it took to check for face.
      delay = Clock.defaultfacecheck - (time.time() - elapse)
      #only delay if time left to delay for.
      if delay > 0.0 :
        time.sleep(delay)

  def weatherthread(self):
    '''Update the weather every n minutes.'''
    while self._running:
      self.UpdateWeather()
      elapse = self.tempupdateinterval
      #Check _running flag every second.
      while (elapse > 0.0) and self._running:
        elapse -= 1.0
        time.sleep(1.0)

    print("Weather update thread exit.")

  def save( self ) :
    '''Save options to json file.'''
    with open(Clock.savename, 'w+') as f:
      data = {}
      data['tempon'] = self.tempdisplay
      data['duration'] = self.displayduration
      data['tempduration'] = self.tempdisplaytime
      data['interval'] = self.tempdisplayinterval
      data['update'] = self.tempupdateinterval
      data['location'] = self.location
      data['color'] = self.colorstr
      data['vflip'] = self.vflip
      data['brightness'] = self.brightness
      data['contrast'] = self.contrast
      data['saturation'] = self.saturation
      data['gain'] = self.gain
      data['exposure'] = self.exposure

      dump(data, f)

  def load( self ) :
    '''Load options from json file.'''
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
        self.vflip = data['vflip']
        self.brightness = data['brightness']
        self.contrast = data['contrast']
        self.saturation = data['saturation']
        self.gain = data['gain']
        self.exposure = data['exposure']
    except:
      pass

  def iline( self, sx, sy, ex, ey ) :
    '''Draw a line from sx,sy to ex,ey.'''
    self._dirtydisplay = True
    self._oled.line((int(sx), int(sy)), (int(ex), int(ey)), 1)

  def drawseg( self, pos, seg, wh ) :
    '''Draw given segment at pos with given size of wh (represents both width and height).
       main line is drawn then if size is large enough 2 shorter lines are drawn on each side of it.'''
    x,y,d = seg #Get position multiply and direction of 0 or 1.
    x = x * wh + pos[0]
    y = y * wh + pos[1]
    #Horizontal line.
    if d == 0:
      sx = x + Clock.segadjust
      ex = sx + wh - Clock.segadjust
      self.iline(sx, y + 1, ex, y + 1)
      #shorten line by 1 on each end.
      sx += 1
      ex -= 1
      #If size is large enough for 2 lines then draw one.
      if wh >= Clock.twoline:
        self.iline(sx, y, ex, y)
      #if large enough to 3 then draw the final line.
      if wh >= Clock.threeline :
        self.iline(sx, y + 2, ex, y + 2)
    else:
      #Vertical line.
      sy = y + 1
      ey = sy + wh - 1
      self.iline(x + 1, sy, x + 1, ey)
      #shorten line by 1 on each end.
      sy += 1
      ey -= 1
      #if large enough to 3 then draw the final line.
      if wh >= Clock.twoline:
        self.iline(x, sy, x, ey)
      #if large enough to 3 then draw the final line.
      if wh >= Clock.threeline :
        self.iline(x + 2, sy, x + 2, ey)

  def drawsegs( self, pos, seglist, wh ) :
    '''Draw segments in seglist at pos with given size of wh.'''
    for s in seglist:
      self.drawseg(pos, Clock.segs[s], wh)

  def draw( self ) :
    '''Draw the display.'''
    if self.on :
      self._oled.clear()
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

      #Draw hh, mm and am/pm.
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
        self._oled.fillrect(pos, (3,3), 1)

      #Draw the colon in between hh and mm every second for a second.
      #This will cause it to blink.
      if (self.digits[5] & 1) == 1:
        sx = (Clock.digitpos[1] + 1.0 + Clock.digitpos[2]) / 2
        sy = (self.wh // 3) * 2
        p = (int(sx * self.wh) + x, y + sy)
        drawrect(p)
        sy += sy
        p = (p[0], y + sy)
        drawrect(p)

      self._oled.display() #Update the display.

  def UpdateWeather( self ) :
    '''Update weather by reading the URL
    "https://query.yahooapis.com/v1/public/yql?q=select%20item.condition%20from%20weather.forecast%20where%20woeid%3D' + str(aLoc) + '&format=json'
    '''
    try:
      req = urlopen(self._url, None, 2)
      d = req.read()
      j = loads(d.decode('utf-8'))
      cond = j['query']['results']['channel']['item']['condition']
      self.temp = int(cond['temp'])
      self.text = cond['text']
    except Exception as e:
      print(e)

  def Update( self, dt ) :
    '''Run update of face check, time and display state.'''
    #Only check for a face every so often.  If found turn display on.
    self._checktime -= dt
    if self._checktime <= 0.0 :
      self._checktime = 2.0
#      print("Checking Face")
      if checkface.Check(self._checker) :
        print("  face found!")
        self.on = True #Turn display on.

    #Read time and save in digits.
    t = time.localtime()
    h = t.tm_hour
    m = t.tm_min
    s = t.tm_sec
    self._h = h
    self._m = m

    apm = 0
    #display temp in main display if it's time.
    if self.tempdisplay and ((s % self.tempdisplayinterval) < self.tempdisplaytime) :
      h = self.temp // 100                      #Clear hours to 0.
      m = self.temp % 100                       #Set minutes to the temperature (only works for positive temps).
      apm = 3                                   #Set am/pm to deg symbol.
    elif h >= 12: #if pm then set to pm.
      apm = 1
      if h > 12:
        h -= 12                                 #12 hour display.

    self.digits = (h // 10, h % 10, m // 10, m % 10, apm, s)

    if self.on :
      #if display on the update the on time and display.
#      self._onlock.acquire()
      self._ontime -= dt
      rem = self._ontime
#      self._onlock.release()

      #if time's up then clear the display.
      if rem <= 0 :
        self._oled.clear()
        self._oled.display()

  def run( self ) :
    '''Run the clock.'''
    try:
      self.iron = True
      self._wtthread.start()
      self._settingsthread.start()

      while self._running:
        if self._haskeyboard and keyboard.is_pressed('q') :
          self._running = False
          print("quitting.")
        else:
          ct = time.time()
          dt = min(1.0, ct - self._prevtime) #clamp max elapsed time to 1 second.
          self._prevtime = ct

          self.Update(dt)
          self.draw()

          delay = 0.2 - (time.time() - ct)
          if delay > 0.0 :
            time.sleep(delay)
    except KeyboardInterrupt:
      print("ctrl-c exit.")
      self._running = False

    self.save()                                 #Save current settings.
#    self._sthread.join()
    #Wait the background threads to end.
    print("Shutting down threads.")
    self._wtthread.join()
    self._settingsthread.join()
    self.iron = False

def run(  ) :
    print("Running")
    c = Clock()
    c.run()

run()
print("Clock done.")