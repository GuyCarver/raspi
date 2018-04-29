#!/usr/bin/env python3
#oled display of clock with temperature.
#Display on/off is controlled by mlx90614 IR temperature sensor.
#also web hosted settings IE: 192.168.2.6?:8080 in a browser will pull up the settings page.
#This module must be run under sudo or the settings server will fail from permission exception.
#Auto start using Crontab.  Added the following line with the command:
# crontab -e (to edit the crontab file)
# @reboot sudo /home/pi/projects/clock/clock.py > /home/pi/projects/clock/clock.log

import os, sys
import RPi.GPIO as GPIO
from oled import *
import time, datetime
from urllib.request import urlopen
from json import loads, dump, load
from threading import Thread #,Lock
import keyboard
import settings
import woeid
from mlx90614 import mlx, c2f
from terminalfont import *
from buttons import button
import wifi

#todo: Maybe add a light sensor to control when clock stays on?
#todo: Hour setting toggle display of mlx90614 values?  Could add variance setting to it.

#Weather codes
#Code  Description
#0 tornado
#1 tropical storm
#2 hurricane
#3 severe thunderstorms
#4 thunderstorms
#5 rain/snow
#6 rain/sleet
#7 snow/sleet
#8 frzng drizzle
#9 drizzle
#10  frzng rain
#11  showers
#12  showers
#13  flurries
#14  light snow
#15  blowing snow
#16  snow
#17  hail
#18  sleet
#19  dust
#20  foggy
#21  haze
#22  smoky
#23  blustery
#24  windy
#25  cold
#26  cloudy
#27  mostly cldy
#28  mostly cldy
#29  partly cldy
#30  partly cldy
#31  clear
#32  sunny
#33  fair
#34  fair
#35  rain/hail
#36  hot
#37  isolated tstorm
#38  sctrd tstorm
#39  sctrd tstorm
#40  sctrd showers
#41  heavy snow
#42  sctrd snow
#43  heavy snow
#44  partly cloudy
#45  tshowers
#46  snow
#47  isolated tshowers
#3200  not available

class Clock:

  #x,y,dir x,y are mulipliers. Dir = (0=right, 1=down)
  #  0    7
  #1   2    8
  #  3    9
  #4   5    10
  #  6   11
  segs = [(0,0,0), (0,0,1), (1,0,1), (0,1,0), (0,1,1), (1,1,1), (0,2,0),
          (1,0,0), (2,0,1), (1,1,0), (2,1,1), (2,2,0)]
  segadjust = 2 #pixels to adjust segment draw position by to simulate a segment display.

  #Lists of segments needed to display 0-9.
  nums = [[0,1,2,4,5,6], [2,5], [0,2,3,4,6], [0,2,3,5,6], [1,2,3,5],
          [0,1,3,5,6], [0,1,3,4,5,6], [0,2,5], [0,1,2,3,4,5,6], [0,1,2,3,5]]

  #apm and deg symbol
  apm = [(0,1,2,3,4,5), (0,1,2,3,4), (0,1,2,4,5,7,8,10), (0,1,2,3)]

  #Position x mulipliers of the clock digits and am/pm.
  digitpos = [0.0, 1.35, 3.2, 4.55, 6.15]
  twoline = 7     #minimum size for 2 line width of segment.
  threeline = 10  #minimum size for 3 line width of segment.
  tempsize = 6    #Size in pixels of temp half segment.
  tmconvert = '{:02d}:{:02d}'
  dtconvert = '{}-{:02d}-{:02d}'
  colorconvert = '#{:06x}'
  savename = '/home/pi/projects/clock/clock.json'

  #Snooze, Alarm On/Off Switch, Alarm Set, Minute, Hour, Time Set (Update temp)
  buttonids = [12, 5, 6, 13, 19, 26]
  snooze = 0
  alarmonoff = 1
  alarmset = 2
  minuteset = 3
  hourset = 4
  timeset = 5
  #Seconds for different rates of increment.
  incratem = [(8.0, .1), (5.0, .2), (1.0, .3), (0.0, 0.5)]
  incrateh = [(1.0, .2), (0.0, 1.0)]
  fiverate = 7
  fifteenrate = 10

  #mlx90614 defaults.
  defaultobjectcheck = 0.75   #Check for object every n seconds.
  defaultdisplaydur = 10.0    #Default time in seconds display stays on after face detection.
  defaultbasetemp = 70.0      #70 degrees F.
  defaultvariance = 4         #N degrees F above ambient for display trigger.
  objecttempsetdelay = 10.0   #Seconds before base temp is reset to current temperature.

  #Clock defaults.
  defaultalwaysontimes = (7 * 60, 19 * 60) #Times between which the display is always on, and object detection isn't necessary.
  defaulttempinterval = 30    #seconds to wait before tempurature update.
  defaulttempdur = 3          #Duration of main temp display.
  defaulttempupdate = 5.0     #Time between tempurature querries.
  defaultdim = 0x7F           #Default value for brightness 0-0xFF.
  alarmpin = 18               #GPIO18 pin is PWM for alarm buzzer.
  alarmfreq = 700             #Just play with this # til you get something nice.
  alarmdutycycle = 75         #Between 0-100 but 0 and 100 are silent.
  beepfreq = 1.0              #Frequency in seconds for beep.

  _tabname = ['', 'ALARM', 'ALWAYS ON', 'ALWAYS OFF', 'VARIANCE', 'SENSOR']

  #Abbreviated text for weather condition codes.
  _weathertext = [
    'tornado',
    'tpcl storm',
    'hurricane',
    'svr t-storm',
    't-storm',
    'rain/snow',
    'rain/sleet',
    'snow/sleet',
    'frzng drzzle',
    'drizzle',
    'frzng rain',
    'showers',
    'showers',
    'flurries',
    'light snow',
    'blwng snow',
    'snow',
    'hail',
    'sleet',
    'dust',
    'foggy',
    'haze',
    'smoky',
    'blustery',
    'windy',
    'cold',
    'cloudy',
    'mstly cldy',
    'mstly cldy',
    'prtly cldy',
    'prtly cldy',
    'clear',
    'sunny',
    'fair',
    'fair',
    'rain/hail',
    'hot',
    'istd t-storm',
    'sctd t-storm',
    'sctd t-storm',
    'sctd showers',
    'heavy snow',
    'sctd snow',
    'heavy snow',
    'prtly cldy',
    't-showers',
    'snow',
    'istd t-shwrs',
  ]

  def __init__( self ):
    print("Init")
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(Clock.alarmpin, GPIO.OUT)
    self._buttons = [ button(i) for i in Clock.buttonids ]
    self._pressedtime = 0                         #Used to track amount of time the hour/minute set buttons are pressed.
    self._repeattime = 0                          #Used to auto repeat button toggle when held down.

    self._alarm = GPIO.PWM(Clock.alarmpin, Clock.alarmfreq)
    self._alarmtime = (0, 0) #Hour, Minute.
    self._alarmcheckminute = -1
    self._alarmenabled = False
    self._beep = False
    self._triggered = False
    self._beeptime = Clock.beepfreq

    self._tempdisplayinterval = Clock.defaulttempinterval

    #set properties
    self.tempdisplaytime = Clock.defaulttempdur
    self.tempupdateinterval = Clock.defaulttempupdate
    self.displayduration = Clock.defaultdisplaydur
    self.checkinterval = Clock.defaultobjectcheck
    self.wh = 15  #Size of half of the segment (0-3).  IE: segment 6 is drawn at y of 30 if wh is 15.
    self.pos = (1, 10)
    self.size = (128, 64)

    try:
      self._oled = oled(1)  #1st try later versions of the pi.
    except:
      self._oled = oled(0)  #if those fail we're using the 1st gen maybe?

    self._oled.rotation = 2
    self._oled.dim = Clock.defaultdim

    #wifi stuff.
    self._lvl = -100  #wifi level.
    self._lastsecond = 0

    self._digits = (0, 0, 0, 0, 0, 0)
    self._tempdisplay = True
    self._curtime = (0, 0)
    self.temp = 0
    self.code = 3200
    self.text = 'Sunny'
    self._color = 0x00FFFF
    self._url = ''
    self.location = '21774' #zipcode.
    self._running = True
    self._dirtydisplay = False

    self._weathertimer = 0.0
    self._prevtime = time.time()

    self._ontime = 0.0
    self.on = True
    self._checktime = 0                         #Timer for checking for object.
    self._checker = mlx()
    self._tab = 0 #0 = clock, 1 = alarm, 2 = start time, 3 = stop time

    self._alwaysontimes = [0, 0]
    self.mlxdefaults()
    self.load()

    #If no keyboard we'll get an exception here so turn off keyboard flag.
    try:
      bres = keyboard.is_pressed('q')
      self._haskeyboard = True
    except:
      self._haskeyboard = False

    self._wtthread = Thread(target=self.weatherthread)
    self._settingsthread = Thread(target=self.startsettings)

  def __del__( self ):
    self._oled.clear()
    GPIO.cleanup()

#Alarm properties.
  @property
  def beep( self ):
    '''Return true if alarm sound can currently be heard.'''
    return self._beep

  @beep.setter
  def beep( self, aTF ):
    '''Set alarm beep on/off.'''
    if self._beep != aTF:
      self._beep = aTF
      if self._beep:
        self._alarm.start(Clock.alarmdutycycle)
      else:
        self._alarm.stop()

  @property
  def triggered( self ):
    '''Return true if alarm is currently triggered (beeping).'''
    return self._triggered

  @triggered.setter
  def triggered( self, aTF ):
    '''Set alarm trigger on/off.'''
    if self._triggered != aTF:
      self._triggered = aTF
      self.beep = aTF

  @property
  def alarmenabled( self ):
    '''Return true if alarm is set to go off.'''
    return self._alarmenabled

  @alarmenabled.setter
  def alarmenabled( self, aTF ):
    '''Set alarm on/off.'''
    self._alarmenabled = aTF
    if aTF == False:
      self.triggered = False

  @property
  def alarmtime( self ):
    '''Return (hh,mm) tuple.'''
    return self._alarmtime

  @alarmtime.setter
  def alarmtime( self, aValue ):
    '''Set alarm time (hh,mm) tuple.'''
    self._alarmtime = aValue

  @property
  def alarmhhmm( self ):
    '''Get "hh:mm" in string format (for the settings http server).'''
    return Clock.tmconvert.format(*self._alarmtime)

  @alarmhhmm.setter
  def alarmhhmm( self, aValue ):
    try:
      hh, mm = aValue.split(':')
      self.alarmtime = (int(hh), int(mm))
    except:
      self.alarmtime = (0,0)
#END Alarm properties.

  @property
  def alwaysontimes( self ):
    return self._alwaysontimes

  @alwaysontimes.setter
  def alwaysontimes( self, aValue ):
    start, stop = aValue
    start = min(stop, start)
    self._alwaysontimes[0] = start
    self._alwaysontimes[1] = stop

  @property
  def alwaysontimeshhmm( self ):
    start, stop = self.alwaysontimes
    start = Clock.tmconvert.format(start // 60, start % 60)
    stop = Clock.tmconvert.format(stop // 60, stop % 60)
    return (start, stop)

  @alwaysontimeshhmm.setter
  def alwaysontimeshhmm( self, aValue ):
    try:
      def cnvt( atime ):
        hh, mm = atime.split(':')
        return (int(hh) * 60) + int(mm)
      self.alwaysontimes = (cnvt(aValue[0]), cnvt(aValue[1]))
    except:
      self.alwaysontimes = (0,0)

  @property
  def on( self ):
    '''Return true if display is currently on.'''
    return self._ontime > 0.0

  @on.setter
  def on( self, aTF ):
    '''Set display time to displayduration if on or 0 if off.'''
    self._ontime = self.displayduration if aTF else 0.0

  @property
  def dim( self ):
    return self._oled.dim

  @dim.setter
  def dim( self, aValue ):
    self._oled.dim = aValue

  def _nextdim( self ):
    '''Cycle through brightness values 0, 0x7F, 0xFE '''
    d = self.dim  + 0x7F
    if d > 0xFF :
     d = 0
    self.dim = d
    self.on = True                                #Turn display on, so we can see the brightness.

  @property
  def tempdisplay( self ):
    '''Return if large temp display is enabled.'''
    return self._tempdisplay

  @tempdisplay.setter
  def tempdisplay( self, aValue ):
    '''Enable/Disable large temperature display.'''
    self._tempdisplay = aValue

  @property
  def tempdisplayinterval( self ):
    '''Get the interval in second for temperature display trigger.'''
    return self._tempdisplayinterval

  @tempdisplayinterval.setter
  def tempdisplayinterval( self, aValue ):
    '''Set the interval in second for temperature display trigger.  Clamped to 60-tempdisplaytime.'''
    self._tempdisplayinterval = min(aValue, 60 - self.tempdisplaytime)

  @property
  def tempdisplaytime( self ):
    '''Get the temperature display duration.'''
    return self._tempdisplaytime

  @tempdisplaytime.setter
  def tempdisplaytime( self, aValue ):
    '''Set the temperature display duration and recalculate tempdisplayinterval.'''
    self._tempdisplaytime = aValue
    self.tempdisplayinterval = self.tempdisplayinterval #Recalculate the temp display interval.

  @property
  def tempupdateinterval( self ):
    '''Get the temperature update interval in minutes.'''
    return self._tempupdateinterval

  @tempupdateinterval.setter
  def tempupdateinterval( self, aValue ):
    '''Set the temperature update interval in minutes.'''
    self._tempupdateinterval = aValue

  @property
  def displayduration( self ):
    '''Get duration of the display after turned on.'''
    return self._displayduration

  @displayduration.setter
  def displayduration( self, aValue ):
    '''Set duration of the display after turned on.'''
    self._displayduration = aValue

  @property
  def checkinterval( self ):
    return self._checkinterval

  @checkinterval.setter
  def checkinterval( self, aValue ):
    '''Set interval in seconds for face check.
       Clamped between 0.1 and 1.0.'''
    self._checkinterval = max(0.1, min(1.0, aValue))

  @property
  def hhmm( self ):
    '''Get "hh:mm" in string format (for the settings http server).'''
    return Clock.tmconvert.format(*self._curtime)

  @hhmm.setter
  def hhmm( self, aValue ):
    '''todo: Convert "hh:mm" into hours/minutes and set the time.'''
    pass

  @property
  def date( self ):
    '''Get "yy-mm-dd" in string format (for the settings http server).'''
    t = datetime.date.today()
    return Clock.dtconvert.format(t.year, t.month, t.day)

  @date.setter
  def date( self, aValue ):
    '''todo: Convert "yy-mm-dd" into year, month, day and set the date.'''
    pass

  @property
  def color( self ):
    '''Get the color in 0x00RRGGBB'''
    return self._color

  @color.setter
  def color( self, aValue ):
    '''Set the color'''
    self._color = aValue

  @property
  def colorstr( self ):
    '''Get the color as a string "#RRGGBB".'''
    return Clock.colorconvert.format(self._color)

  @colorstr.setter
  def colorstr( self, aValue ):
    '''Set the color from a string format "#RRGGBB".'''
    c = int(aValue[1:], 16) #skin the leading # and convert base 16 digits to int.
    self._color = c

  @property
  def location( self ):
    '''Get the location zip.'''
    return self._location

  @location.setter
  def location( self, aLoc ):
    '''Set the location zip and setup the querry url for the weather update thread.'''
    self._location = aLoc
    try:
      wid = woeid.woeidfromzip(aLoc)
    except:
      wid = 2458710 #Set to Frederick MD on error.
      print('error reading woeid from internet.')

    self._url = 'https://query.yahooapis.com/v1/public/yql?q=select%20item.condition%20from%20weather.forecast%20where%20woeid%3D' + str(wid) + '&format=json'

  @property
  def variance( self ):
    return self._variance

  @variance.setter
  def variance( self, aValue ):
    self._variance = aValue

  def mlxdefaults( self ):
    self._basetemp = Clock.defaultbasetemp
    self._variance = Clock.defaultvariance
    self.alwaysontimes = Clock.defaultalwaysontimes

  @property
  def alwayson( self ):
    minutes = (self._curtime[0] * 60) + self._curtime[1]
    return self._alwaysontimes[0] <= minutes < self._alwaysontimes[1]

  def triggerweatherupdate( self ):
    self._weathertimer = 0.0

  def startsettings( self ):
#    print("Starting settings server")
    settings.run(self)

  def weatherthread(self):
    '''Update the weather every n minutes.'''
    waittime = 1.0
    while self._running:
      self.UpdateWeather()
      self._weathertimer = self.tempupdateinterval * 60.0  #Convert minutes to seconds.
      #Check _running flag every second.
      while (self._weathertimer > 0.0) and self._running:
        self._weathertimer -= waittime
        time.sleep(waittime)

    print("Weather update thread exit.")

  def save( self ):
    '''Save options to json file.'''
    try:
      with open(Clock.savename, 'w+') as f:
        data = {}
        data['tempon'] = self.tempdisplay
        data['duration'] = self.displayduration
        data['tempduration'] = self.tempdisplaytime
        data['interval'] = self.tempdisplayinterval
        data['objectcheck'] = self.checkinterval
        data['update'] = self.tempupdateinterval
        data['location'] = self.location
        data['color'] = self.colorstr
        data['alarm'] = self.alarmtime
        data['variance'] = self.variance
        data['alwayson'] = self.alwaysontimes
        data['dim'] = self.dim

        dump(data, f)
    except:
      pass

  def load( self ):
    '''Load options from json file.'''
    try:
      with open(Clock.savename, 'r') as f:
        data = load(f)
        self.tempdisplay = data['tempon']
        self.tempdisplayinterval = data['interval']
        self.displayduration = data['duration']
        self.tempdisplaytime = data['tempduration']
        self.tempupdateinterval = data['update']
        self.colorstr = data['color']
        self.location = data['location']
        self.checkinterval = data['objectcheck']
        self.alarmtime = data['alarm']
        self.variance = data['variance']
        self.alwaysontimes = data['alwayson']
        self.dim = data['dim']
    except:
      pass

  def iline( self, sx, sy, ex, ey ):
    '''Draw a line from sx,sy to ex,ey.'''
    self._dirtydisplay = True
    self._oled.line((int(sx), int(sy)), (int(ex), int(ey)), 1)

  def drawseg( self, pos, seg, wh ):
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
      if wh >= Clock.threeline:
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
      if wh >= Clock.threeline:
        self.iline(x + 2, sy, x + 2, ey)

  def drawsegs( self, pos, seglist, wh ):
    '''Draw segments in seglist at pos with given size of wh.'''
    for s in seglist:
      self.drawseg(pos, Clock.segs[s], wh)

  def draw( self ):
    '''Draw the display.'''
    if self.on:
      self._oled.clear()
      x, y = self.pos

      #Draw an hour or minute digit.
      def drawdig( anum ):
        p = (x + int(self.wh * Clock.digitpos[anum]), y)
        self.drawsegs(p, Clock.nums[self._digits[anum]], self.wh)

      #Draw am or pm depending on the hour.
      def drawapm( anum ):
        wh = self.wh // 2
        p = (x + int(self.wh * Clock.digitpos[anum]), y)
        d = self._digits[anum]
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

      #If alarm enabled print the bell icon.
      if self._alarmenabled:
        p = (x + int(self.wh * Clock.digitpos[4]), y + 4 + self.wh)
        self._oled.char(p, '\x1F', True, terminalfont, 1)

      #Draw wifi level indicator
      if self._lvl > 0:
        p = (x + int(self.wh * Clock.digitpos[4]) + 18, y + 4 + self.wh)
        self._oled.char(p, chr(self._lvl), True, wifi.font, 1)

      #If we want to display the temperature then do so at the bottom right.
      if self.tempdisplay:
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
      def drawrect( pos ):
        self._oled.fillrect(pos, (3,3), 1)

      drawtext = self._tab == 0                 #If tab 0, we don't blink the tab name.

      #Draw the colon in between hh and mm every second for a second.
      #This will cause it to blink.
      if self._digits[5] & 1:
        sx = (Clock.digitpos[1] + 1.0 + Clock.digitpos[2]) / 2
        sy = (self.wh // 3) * 2
        p = (int(sx * self.wh) + x, y + sy)
        drawrect(p)
        sy += sy
        p = (p[0], y + sy)
        drawrect(p)

        drawtext = True

      if drawtext and Clock._tabname[self._tab] != '':
        #Draw the display tab name.
        p = (x, y + 10 + (self.wh * 2))
        self._oled.text(p, Clock._tabname[self._tab], 1, terminalfont)

      self._oled.display() #Update the display.

  def UpdateWeather( self ):
    '''Update weather by reading the URL
    "https://query.yahooapis.com/v1/public/yql?q=select%20item.condition%20from%20weather.forecast%20where%20woeid%3D' + str(aLoc) + '&format=json'
    '''
    try:
      req = urlopen(self._url, None, 2)
      d = req.read()
      j = loads(d.decode('utf-8'))
      cond = j['query']['results']['channel']['item']['condition']
      self.temp = int(cond['temp'])
      self.code = int(cond['code'])
      #If a good code, then set tab 0 name to the abbreviated weather text.
      if self.code < len(Clock._weathertext):
        Clock._tabname[0] = Clock._weathertext[self.code]

      self.text = cond['text']                    #Get full weather text.
    except Exception as e:
      print(e)

  def UpdateAlarm( self, dt ):
    '''Update the alarm state.'''
    ah, am = self.alarmtime
    #If alarm is currently triggered then update it.
    h, m = self._curtime

    if self.triggered:
      #Turn alarm off as soon as hour or minute change.
      if h != ah or m != am:
        self.triggered = False
      else:
        self._beeptime -= dt
        if self._beeptime <= 0:
          self.beep = not self.beep  #toggle sound on/off at beepfreq.
          self._beeptime = Clock.beepfreq
    #If alarm is set then once we hit the hour and minute start triggered.
    #But only check on every new minute.
    elif self.alarmenabled and m != self._alarmcheckminute:
      self._alarmcheckminute = m
      if h == ah and m == am:
        self.triggered = True

  @staticmethod
  def _pmadjust( aHour ):
    '''  '''
    apm = 0
    if aHour >= 12: #if pm then set to pm.
      apm = 1
      if aHour > 12:
        aHour -= 12                             #12 hour display.
    elif aHour == 0:
      aHour = 12

    return (aHour, apm)

  def checkinc( self, aState, rates, dt ):
    '''Determine if it's time to increment a value based on button state and time depressed.'''

    #We assume button is pressed if this function is called.  So this determines if it was just pressed.
    if button.ischanged(aState):
      self._pressedtime = 0.0
      self._repeattime = 0.0
      return 1

    self._pressedtime += dt                     #Update amount of time the button has been pressed.
    self._repeattime += dt                      #Update amount of time until repeat of button press.

    rate = 0.0

    #Look up repeat rate based on pressed time.
    for v in rates:
      if self._pressedtime >= v[0]:
        rate = v[1]
        break

    #If repeat time is > repeate rate then do a repeat.
    if self._repeattime > rate:
      self._repeattime = 0
      return 1

    return 0

  def checkforobject( self ):
    # Perhaps use the ambient temperature as the base?

    res = False
    #Get object temperature.
    tmp = self._checker.objecttemp()

    # If temperature varies by the expected amount above base temperature then display is on.
    if tmp >= self._basetemp + self.variance:
      res = True

      if self._objectfoundtime == 0:
        self._objectfoundtime = self._prevtime
      else:
        dt = self._prevtime - self._objectfoundtime
        if dt >= Clock.objecttempsetdelay:
          self._objectfoundtime = 0
          self._basetemp = tmp
    else:
      self._objectfoundtime = 0

      # If temperature < base then immediately set new base.
      if tmp < self._basetemp:
        self._basetemp = tmp

    # else if temperature > base for given amount of time, then set as new base.
    return res

  def updatebuttons( self ) :
    for b in self._buttons:
      b.update()

  def processalarmbutton( self ):
    '''Use alarm button to switch between displays.  Snooze button exits back to time.'''

    #If snooze button jest pressed, show tab 0 (time).
    if self._buttons[Clock.snooze].pressed:
      if self._tab > 0:
        self._tab = 0
        self.save() #Save any potential changes on exit back to time.
    else:
      #alarmset button cycles through tabs.
      if self._buttons[Clock.alarmset].pressed:
        self._tab += 1
        #Note: Tabs - 1 cuz we don't cycle through the sensor tab.
        if self._tab >= len(Clock._tabname) - 1:
          self._tab = 0
          self.save()  #Save when we wrap around.

  def Update( self, dt ):
    '''Run clock update'''

    self.updatebuttons()

    self._alarmenabled = self._buttons[Clock.alarmonoff].on
    self.processalarmbutton()

    #Read time and save in digits.
    t = time.localtime()
    self._curtime = (t.tm_hour, t.tm_min)
    s = t.tm_sec

    apm = 0

    #Update button pressed states.
    tbuttonstate = self._buttons[Clock.timeset].state
    msetstate = self._buttons[Clock.minuteset].state
    hsetstate = self._buttons[Clock.hourset].state

    #Regular time display.
    if self._tab == 0:
      #Minute button updates dimness.
      if msetstate == button.CHANGE :
        self._nextdim()

      h, m = self._curtime                      #Display current time.

      #If snooze button pressed just enable the display.
      if self._buttons[Clock.snooze].on:
        self.on = True;                         #Turn display on.
        self.triggered = False                  #Turn alarm off if it was triggered.
      #else check for a face for display enable.
      elif self.alwayson:
        self.on = True
      else:
        self._checktime -= dt
        if self._checktime <= 0.0:
          self._checktime = self.checkinterval
          #Check for object temperature change.
          if self.checkforobject():
            self.on = True          #Turn display on.
            self.triggered = False  #Make sure alarm is off.

      #Update temp and display temp in main display if it's time.
      if self.tempdisplay:
        #If timeset button is pressed during regular display we trigger temp update.
        if button.justpressed(tbuttonstate):
          self.triggerweatherupdate()

        #If hour button is pressed we switch to sensor display tab.
        if button.justpressed(hsetstate):
          self._tab = 5

        #If time to display then do so.
        if ((s % self.tempdisplayinterval) < self.tempdisplaytime):
          h = self.temp // 100                  #Clear hours to 0.
          m = self.temp % 100                   #Set minutes to the temperature (only works for positive temps).
          apm = 3                               #Set am/pm to deg symbol.
    #Variance edit.
    elif self._tab == 4:
      self.on = True                           #Turn display on so we can see.
      m = self._variance
      h = 0
      apm = 3

      if button.ison(msetstate): #If minuteset pressed then increase minutes.
        if self.checkinc(msetstate, Clock.incratem, dt):
          #If time button pressed, go backwards.
          if button.ison(tbuttonstate):
            m -= 1
            if m < 1:
              m += 8
          else:
            m += 1
            if m > 8:
              m -= 8
          self._variance = m
    #Sensor data display tab.
    elif self._tab == 5:
      self.on = True                            #Turn display on so we can see.
      m = int(c2f(self._checker.objecttemp()))
      h = int(c2f(self._checker.ambienttemp()))
      apm = 3

      if button.justpressed(hsetstate):
        self._tab = 0

      #Alarm, Start and Stop times.
    else:
      self.on = True;                           #Turn display on so we can see alarm time setting.

      if self._tab == 1:
        h, m = self._alarmtime
      elif self._tab == 2:
        m = self.alwaysontimes[0]
        h = m // 60
        m = m % 60
      else:
        m = self.alwaysontimes[1]
        h = m // 60
        m = m % 60

      change = False
      if button.ison(msetstate): #If minuteset pressed then increase minutes.
        if self.checkinc(msetstate, Clock.incratem, dt):
          #If time button pressed, go backwards.
          if button.ison(tbuttonstate):
            m -= 1
            #Wrap around at 0 and decrease hour.
            if m < 0:
              m += 60
              h = (h - 1) % 24
          else:
            m += 1
            #Wrap around at 60 and increase hour.
            if m > 59:
              m = m % 60
              h = (h + 1) % 24
          change = True
      else:
        #If hourset pressed then increase hour.
        if button.ison(hsetstate) and self.checkinc(hsetstate, Clock.incrateh, dt):
          #If time button pressed, decrement hour.
          h = (h + (-1 if button.ison(tbuttonstate) else 1)) % 24
          change = True

      if change:
        if self._tab == 1:
          self._alarmtime = (h, m)
        elif self._tab == 2:
          self.alwaysontimes = (h * 60 + m, self._alwaysontimes[1])
        else:
          self.alwaysontimes = (self._alwaysontimes[0], h * 60 + m)

    #If we want to adjust time from 24 to 12 hour then do so.
    # apm will be set to 3 (deg) if not.
    if apm == 0:
      h, apm = self._pmadjust(h)

    self._digits = (h // 10, h % 10, m // 10, m % 10, apm, s)

    if self.on:
      #Every second we'll check wifi signal level.
      if ((s % 15) == 0) and (s != self._lastsecond):
        self._lastsecond = s
        self._lvl = wifi.level()

      #if display on then update the on time and display.
      self._ontime -= dt
      rem = self._ontime

      #if time's up then clear the display.
      if rem <= 0:
        self._oled.clear()
        self._oled.display()

      #Don't update alarm while we are setting it.
      if self._tab != 1:
        self.UpdateAlarm(dt)

  def run( self ):
    '''Run the clock.'''
    try:
      self._wtthread.start()
      self._settingsthread.start()

      while self._running:
        if self._haskeyboard and keyboard.is_pressed('q'):
          self._running = False
          print("quitting.")
        else:
          ct = time.time()
          dt = min(1.0, ct - self._prevtime) #clamp max elapsed time to 1 second.
          self._prevtime = ct

          self.Update(dt)
          self.draw()

          delay = 0.2 - (time.time() - ct)
          if delay > 0.0:
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
    self._oled.clear()
    self._oled.display()

def run(  ):
    print("Running")
    c = Clock()
    c.run()

run()
print("Clock done.")

