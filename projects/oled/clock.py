#!/usr/bin/env python3
#oled display of clock with temperature.
#Display on/off is controlled by face detection.
#also web hosted settings IE: 192.168.2.62 in a browser will pull up the settings page.
#This module must be run under sudo or the settings server will fail from permission exception.
#Auto start using Crontab.  Added the following line with the command:
# crontab -e (to edit the crontab file)
# @reboot sudo /home/pi/projects/oled/clock.py > /home/pi/projects/oled/clock.log

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
import woeid
from seriffont import seriffont
from buttons import button

#done: Need to speed up the checkface system.  It takes way too long at the moment.  May need to go with a better raspi.
# switched to haarcascade_frontalface_default.xml and reduced image scale to .25 and this sped things up as well as improved accuracy.
#done: Try checkface from the main thread to see if it's more efficient.  It's messing with display at the moment.
#  Did this and it definitely worked better so I'm staying with it.

#todo: What is the time button going to do?  We don't need it for setting the time.
#todo: The scale should be from .25 to 1.0.  The optimal so far is .5.  But anything below .25 is useless.
#todo: For testing purposes it would be nice if we could take a picture from the camera using the "time" button.
#  Then if we could see it on the web page I could help debug some issues.

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

  #Snooze, Alarm On/Off Switch, Alarm Set, Minute, Hour, Time Set (Update temp)
  buttonids = [12, 5, 6, 13, 19, 26]
  snooze = 0
  alarmonoff = 1
  alarmset = 2
  minuteset = 3
  hourset = 4
  timeset = 5
  #Seconds for different rates of increment.
  incratem = [(8.0, .2), (5.0, .3), (2.0, .5), (0.0, 0.75)]
  incrateh = [(1.0, .2), (0.0, 1.0)]
  fiverate = 7
  fifteenrate = 10

  #Camera defaults.
  defaultcontrast = 100.0
  defaultsaturation = 100.0
  defaultbrightness = 75.0
  defaultgain = 25.0
  defaultexposure = -1.0
  defaultvflip = False
  defaultscale = 0.25
  defaultfacecheck = 0.75      #Check for face every n seconds.
  defaultdisplaydur = 10.0     #Default time in seconds display stays on after face detection.

  #Clock defaults.
  defaulttempinterval = 30    #seconds to wait before tempurature update.
  defaulttempdur = 3          #Duration of main temp display.
  defaulttempupdate = 5.0     #Time between tempurature querries.
  ledcontrolpin = 4           #GPIO4 pin controls secondary IR LEDs.
  alarmpin = 18               #GPIO18 pin is PWM for alarm buzzer.
  alarmfreq = 700             #Just play with this # til you get something nice.
  alarmdutycycle = 75         #Between 0-100 but 0 and 100 are silent.
  beepfreq = 1.0              #Frequency in seconds for beep.

  def __init__( self ) :
    print("Init")
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(Clock.ledcontrolpin, GPIO.OUT)
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
    self.checkinterval = Clock.defaultfacecheck
    self.wh = 15  #Size of half of the segment (0-3).  IE: segment 6 is drawn at y of 30 if wh is 15.
    self.pos = (5, 10)
    self.size = (128, 64)

    try:
      self._oled = oled(1)  #1st try later versions of the pi.
    except:
      self._oled = oled(0)  #if those fail we're using the 1st gen maybe?

    self._oled.rotation = 2
    self.digits = (0, 0, 0, 0, 0, 0)
    self._tempdisplay = True
    self._curtime = (0, 0)
    self.temp = 0
    self.text = 'Sunny'
    self._color = 0x00FFFF
    self._url = ''
    self.location = '21774' #zipcode.
    self.load()
    self._running = True
    self._ontime = 0.0
    self.on = True
    self._dirtydisplay = False
    self._checktime = Clock.defaultfacecheck

    self._weathertimer = 0.0
    self._prevtime = time.time()

    try:
      self._checker = checkface.Create()
#      checkface.SetDisplay(self._checker, True)
    except:
      self._checker = None
      print("Camera setup error.")

    self._iron = False
    self.cameradefaults()

    #If no keyboard we'll get an exception here so turn off keyboard flag.
    try:
      bres = keyboard.is_pressed('q')
      self._haskeyboard = True
    except:
      self._haskeyboard = False

    self._wtthread = Thread(target=self.weatherthread)
    self._settingsthread = Thread(target=self.startsettings)

  def __del__( self ) :
    self.iron = False
    self._oled.clear()
    GPIO.cleanup()

#Alarm properties.
  @property
  def beep( self ) :
    '''Return true if alarm sound can currently be heard.'''
    return self._beep

  @beep.setter
  def beep( self, aTF ) :
    '''Set alarm beep on/off.'''
    if self._beep != aTF :
      self._beep = aTF
      if self._beep:
        self._alarm.start(Clock.alarmdutycycle)
      else:
        self._alarm.stop()

  @property
  def triggered( self ) :
    '''Return true if alarm is currently triggered (beeping).'''
    return self._triggered

  @triggered.setter
  def triggered( self, aTF ) :
    '''Set alarm trigger on/off.'''
    if self._triggered != aTF :
      self._triggered = aTF
      self.beep = aTF

  @property
  def alarmenabled( self ) :
    '''Return true if alarm is set to go off.'''
    return self._alarmenabled

  @alarmenabled.setter
  def alarmenabled( self, aTF ) :
    '''Set alarm on/off.'''
    self._alarmenabled = aTF

  @property
  def alarmtime( self ) :
    '''Return (hh,mm) tuple.'''
    return self._alarmtime

  @alarmtime.setter
  def alarmtime( self, aValue ) :
    '''Set alarm time (hh,mm) tuple.'''
    self._alarmtime = aValue

  @property
  def alarmhhmm( self ) :
    '''Get "hh:mm" in string format (for the settings http server).'''
    return Clock.tmconvert.format(*self._alarmtime)

  @alarmhhmm.setter
  def alarmhhmm( self, aValue ) :
    try:
      hh, mm = aValue.split(':')
      self.alarmtime = (int(hh), int(mm))
    except:
      self.alarmtime = (0,0)
#END Alarm properties.

  @property
  def iron( self ) :
    '''Return true if IR LEDs are currently on.'''
    return self._iron

  @iron.setter
  def iron( self, aTF ) :
    '''Set secondary IR LEDs on/off.'''
    if self._iron != aTF :
      self._iron = aTF
      GPIO.output(Clock.ledcontrolpin, GPIO.HIGH if aTF else GPIO.LOW)

  @property
  def on( self ) :
    '''Return true if display is currently on.'''
    return self._ontime > 0.0

  @on.setter
  def on( self, aTF ) :
    '''Set display time to displayduration if on or 0 if off.'''
    self._ontime = self.displayduration if aTF else 0.0

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
  def checkinterval( self ) :
    return self._checkinterval

  @checkinterval.setter
  def checkinterval( self, aValue ) :
    '''Set interval in seconds for face check.
       Clamped between 0.25 and 3.0.'''
    self._checkinterval = max(0.25, min(3.0, aValue))

  @property
  def hhmm( self ) :
    '''Get "hh:mm" in string format (for the settings http server).'''
    return Clock.tmconvert.format(*self._curtime)

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
    '''Get the location zip.'''
    return self._location

  @location.setter
  def location( self, aLoc ) :
    '''Set the location zip and setup the querry url for the weather update thread.'''
    self._location = aLoc
    try:
      wid = woeid.woeidfromzip(aLoc)
    except:
      wid = 2458710 #Set to Frederick MD on error.
      print('error reading woeid from internet.')

    self._url = 'https://query.yahooapis.com/v1/public/yql?q=select%20item.condition%20from%20weather.forecast%20where%20woeid%3D' + str(wid) + '&format=json'

#Camera properties.
  @property
  def cameraok( self ) :
    '''Return true if camera is ok.'''
    return checkface.Ok(self._checker)

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
  def scale( self ) :
    '''Get camera scale.'''
    return checkface.GetScale(self._checker)

  @scale.setter
  def scale( self, aValue ) :
    '''Set camera scale.'''
    checkface.SetScale(self._checker, aValue)

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

  def cameradefaults( self ) :
    self.scale = Clock.defaultscale
    self.vflip = Clock.defaultvflip
    self.contrast = Clock.defaultcontrast
    self.saturation = Clock.defaultsaturation
    self.gain = Clock.defaultgain
    self.exposure = Clock.defaultexposure
    self.brightness = Clock.defaultbrightness
#END Camera properties.

  def triggerweatherupdate( self ) :
    self._weathertimer = 0.0

  def startsettings( self ) :
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


  def save( self ) :
    '''Save options to json file.'''
    with open(Clock.savename, 'w+') as f:
      data = {}
      data['tempon'] = self.tempdisplay
      data['duration'] = self.displayduration
      data['tempduration'] = self.tempdisplaytime
      data['interval'] = self.tempdisplayinterval
      data['facecheck'] = self.checkinterval
      data['update'] = self.tempupdateinterval
      data['location'] = self.location
      data['color'] = self.colorstr
      data['vflip'] = self.vflip
      data['brightness'] = self.brightness
      data['contrast'] = self.contrast
      data['saturation'] = self.saturation
      data['gain'] = self.gain
      data['exposure'] = self.exposure
      data['scale'] = self.scale
      data['alarm'] = self.alarmtime

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
        self.colorstr = data['color']
        self.vflip = data['vflip']
        self.brightness = data['brightness']
        self.contrast = data['contrast']
        self.saturation = data['saturation']
        self.gain = data['gain']
        self.exposure = data['exposure']
        self.scale = data['scale']
        self.location = data['location']
        self.checkinterval = data['facecheck']
        self.alarmtime = data['alarm']
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
        self.drawsegs(p, Clock.nums[self.digits[anum]], self.wh)

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

      #If alarm enabled print the bell icon.
      if self._alarmenabled :
        p = (x + int(self.wh * Clock.digitpos[4]), y + 4 + self.wh)
        self._oled.char(p, '\x1F', True, seriffont, (1, 1))

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

  def UpdateAlarm( self, dt ) :
    '''Update the alarm state.'''
    ah, am = self.alarmtime
    #If alarm is currently triggered then update it.
    h, m = self._curtime

    if self.triggered :
      #Turn alarm off as soon as hour or minute change.
      if h != ah or m != am :
        self.triggered = False
      else:
        self._beeptime -= dt
        if self._beeptime <= 0 :
          self.beep = not self.beep  #toggle sound on/off at beepfreq.
          self._beeptime = Clock.beepfreq
    #If alarm is set then once we hit the hour and minute start triggered.
    #But only check on every new minute.
    elif self.alarmenabled and m != self._alarmcheckminute :
      self._alarmcheckminute = m
      if h == ah and m == am :
        self.triggered = True

  def checkinc( self, aState, rates, dt ) :
    '''Determine if it's time to increment a value based on button state and time depressed.'''

    #We assume button is pressed if this function is called.  So this determines if it was just pressed.
    if button.ischanged(aState) :
      self._pressedtime = 0.0
      self._repeattime = 0.0
      return 1.0

    self._pressedtime += dt                     #Update amount of time the button has been pressed.
    self._repeattime += dt                      #Update amount of time until repeat of button press.

    rate = 0.0

    #Look up repeat rate based on pressed time.
    for v in rates :
      if self._pressedtime >= v[0] :
        rate = v[1]
        break

    #If repeat time is > repeate rate then do a repeat.
    if self._repeattime > rate :
      self._repeattime = 0
      return 1

    return 0

  def updateir( self ) :
    '''If hour is within night time turn secondary IRs on, else turn off.'''
    h = self._curtime[0]
    onoff = h > 18 or h < 9
    self.iron = onoff

  def Update( self, dt ) :
    '''Run update of face check, time and display state.'''
    #Only check for a face every so often.  If found turn display on.
    state = self._buttons[Clock.alarmonoff].update()
    self._alarmenabled = button.ison(state)

    state = self._buttons[Clock.alarmset].update()
    settingalarm = button.ison(state)

    #Read time and save in digits.
    t = time.localtime()
    self._curtime = (t.tm_hour, t.tm_min)
    s = t.tm_sec

    apm = 0
    apmadjust = True

    #Update button pressed states.
    self._buttons[Clock.timeset].update()

    #Don't bother looking for face if we are setting the alarm
    if settingalarm :
      self.on = True;                           #Turn display on so we can see alarm time setting.
      h, m = self._alarmtime
      state = self._buttons[Clock.minuteset].update()
      change = False
      if button.ison(state) : #If minuteset pressed then increase minutes.
        if self.checkinc(state, Clock.incratem, dt) :
          m += 1
          #Wrap around at 60 and increase hour.
          if m > 59 :
            m = m % 60
            h = (h + 1) % 24
            change = True
      else:
        state = self._buttons[Clock.hourset].update()
        #If hourset pressed then increase hour.
        if button.ison(state) and self.checkinc(state, Clock.incrateh, dt) :
          h = (h + 1) % 24
          change = True
        else:
          #timeset button is used to decrement hour.
          state = self._buttons[Clock.timeset].state
          if button.ison(state) and self.checkinc(state, Clock.incrateh, dt) :
            h = (h - 1) % 24
            change = True
      self._alarmtime = (h, m)
    else:
      #If time set button pressed then set checkface to save an image.
      if self._buttons[Clock.timeset].pressed :
        print("Capturing Image")
        checkface.SetCapture(self._checker)

      h, m = self._curtime                      #Display current time.

      #If snooze button pressed just enable the display.
      if button.ison(self._buttons[Clock.snooze].update()) :
        self.on = True;                         #Turn display on.
        self.triggered = False                  #Turn alarm off if it was triggered.
      #else check for a face for display enable.
      else:
        self._checktime -= dt
        if self._checktime <= 0.0 :
          self._checktime = self.checkinterval
          self.updateir()
#         print("Checking Face")
          if checkface.Check(self._checker) :
#            print("  face found!")
            self.on = True          #Turn display on.
            self.triggered = False  #Make sure alarm is off.

      #Update temp and display temp in main display if it's time.
      if self.tempdisplay :
        #If timeset button is pressed during regular display we trigger temp update.
        self._buttons[Clock.timeset].update()
        if self._buttons[Clock.timeset].pressed :
          self.triggerweatherupdate()

        #If time to display then do so.
        if ((s % self.tempdisplayinterval) < self.tempdisplaytime) :
          apmadjust = False                     #Not a time we are displaying so don't do 24 hour adjustment.
          h = self.temp // 100                  #Clear hours to 0.
          m = self.temp % 100                   #Set minutes to the temperature (only works for positive temps).
          apm = 3                               #Set am/pm to deg symbol.

    #If we want to adjust time from 24 to 12 hour then do so.
    if apmadjust :
      if h >= 12 : #if pm then set to pm.
        apm = 1
        if h > 12 :
          h -= 12                               #12 hour display.
      elif h == 0:
        h = 12

    self.digits = (h // 10, h % 10, m // 10, m % 10, apm, s)

    if self.on :
      #if display on then update the on time and display.
      self._ontime -= dt
      rem = self._ontime

      #if time's up then clear the display.
      if rem <= 0 :
        self._oled.clear()
        self._oled.display()

    #Don't update alarm while we are settnig it.
    if not settingalarm :
      self.UpdateAlarm(dt)

  def run( self ) :
    '''Run the clock.'''
    try:
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
    self.iron = False #Turn secondary IR LEDS off.
    self._oled.clear()
    self._oled.display()

def run(  ) :
    print("Running")
    c = Clock()
    c.run()

run()
print("Clock done.")

