#PC version of the clock display.
#installed pygame, requests, bs4

import os, sys, pygame
from pygame.locals import *
import time, datetime
from urllib.request import urlopen
from json import loads, dump, load
from threading import Thread
import settings
import weather
from terminalfont import terminalfont
from buttons import button

#todo: display duration, temp update interval
# New weather api is at https://weather-ydn-yql.media.yahoo.com/forecastrss.
# Look into openweathermap.org
#So far the best looking one is this.
#https://weather.com/weather/today/l/21774:4:US
#  look for today_nowcard-temp and today_nowcard-phrase div tags.
#Add weather icons

class Clock:

  #x,y,dir x,y are mulipliers. Dir = (0=right, 1=down)
  #  0
  #1   2
  #  3
  #4   5
  #  6
  segs = [(0,0,0), (0,0,1), (1,0,1), (0,1,0), (0,1,1), (1,1,1), (0,2,0),
          (1,0,0), (2,0,1), (1,1,0), (2,1,1), (2,2,0)]
  segadjust  = 2
  nums = [[0,1,2,4,5,6], [2,5], [0,2,3,4,6], [0,2,3,5,6], [1,2,3,5],
          [0,1,3,5,6], [0,1,3,4,5,6], [0,2,5], [0,1,2,3,4,5,6], [0,1,2,3,5]]

  apm = [(0,1,2,3,4,5), (0,1,2,3,4), (0,1,2,4,5,7,8,10), (0,1,2,3)]

  digitpos = [0.0, 1.35, 3.2, 4.55, 6.15]
  twoline = 7
  threeline = 10
  tempsize = 6
  tmconvert = '{:02d}:{:02d}'
  dtconvert = '{}-{:02d}-{:02d}'
  colorconvert = '#{:06x}'
  fname = 'clock.json'

  #Snooze, Alarm On/Off Switch, Alarm Set, Minute, Hour, Time Set (Update temp)
  buttonids = [1, 7, 0, 2, 3, 6, 4, 5]
  snooze = 0
  alarmonoff = 1
  alarmset = 2
  minuteset = 3
  hourset = 4
  timeset = 5
  extra1 = 6
  extra2 = 7
  #Seconds for different rates of increment.
  incratem = [(8.0, .1), (5.0, .2), (1.0, .3), (0.0, 0.5)]
  incrateh = [(1.0, .2), (0.0, 1.0)]
  fiverate = 7
  fifteenrate = 10

  defaultalwaysontimes = (7 * 60, 19 * 60) #Times between which the display is always on, and object detection isn't necessary.

  _tabname = ['', 'ALARM', 'ALWAYS ON', 'ALWAYS OFF', 'VARIANCE']
  _conditionlen = 13                            #Maximum string length for condition.

  #Clock defaults.
  defaulttempinterval = 30                      #seconds to wait before tempurature update.
  defaulttempdur = 3                            #Duration of main temp display.
  defaulttempupdate = 5.0                       #Time between tempurature querries.
  defaultdisplaydur = 5.0                       #Default time in seconds display stays on after face detection.
  beepfreq = 1.0                                #Frequency in seconds for beep.

  def __init__( self ):
    os.environ['SDL_VIDEO_WINDOW_POS'] = '910,600'

    self._buttons = [ button(i) for i in Clock.buttonids ]
    self._pressedtime = 0                         #Used to track amount of time the hour/minute set buttons are pressed.
    self._repeattime = 0                          #Used to auto repeat button toggle when held down.

    self._alarmtime = (0, 0) #Hour, Minute.
    self._alarmcheckminute = -1
    self._alarmenabled = False
    self._beep = False
    self._triggered = False
    self._beeptime = Clock.beepfreq

    self._tempdisplayinterval = Clock.defaulttempinterval

    self.tempdisplaytime = Clock.defaulttempdur
    self.tempupdateinterval = Clock.defaulttempupdate
    self.displayduration = Clock.defaultdisplaydur
    self.wh = 15  #Size of half of the segment (0-3).  IE: segment 6 is drawn at y of 30 if wh is 15.
    self.pos = (1, 10)
    self.size = (128, 64)

    pygame.init()
    self.screen = pygame.display.set_mode(self.size)
    self.clock = pygame.time.Clock()

    self.digits = (0, 0, 0, 0, 0, 0)
    self._lastsecond = 0
    self._tempdisplay = True
    self._curtime = (0, 0)
    self.temp = 0
    self.code = 3200
    self.text = 'Sunny'
    self._color = 0x00FFFF
    self.location = '21774'
    self._running = True

    self._alwaysontimes = [0, 0]
    self.alwaysontimes = Clock.defaultalwaysontimes
    self._variance = 2

    self._weathertimer = 0.0
    self._prevtime = time.time()

    self._sounds = []
    self._sounds.append(pygame.mixer.Sound('womp.wav'))
    self._sounds.append(pygame.mixer.Sound('womp2.wav'))

    self.load()

    self._wtthread = Thread(target=self.weatherthread)
    self._settingsthread = Thread(target=self.startsettings)

########### New stuff ###########.
    pygame.joystick.init()
    if pygame.joystick.get_count():
      joy = pygame.joystick.Joystick(0)
      joy.init()
      button.setjoy(joy)

    self._tab = 0 #0 = clock, 1 = alarm, 2 = start time, 3 = stop time
    self.dim = 0x7F

  def __del__( self ):
    button.setjoy(None)

  def processalarmbutton( self ):
    '''Use alarm button to switch between displays.  Snooze button exits back to time.'''
    state = self._buttons[Clock.snooze].update()
    if state == button.CHANGE | button.DOWN:
      if self._tab > 0:
        self._tab = 0
        self.save()
    else:
      state = self._buttons[Clock.alarmset].update()
      if state == button.CHANGE | button.DOWN:
        self._tab += 1
        if self._tab >= len(Clock._tabname):
          self._tab = 0
          self.save()

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
        self._sounds[0].play()
      else:
        self._sounds[1].play()

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
  def dim( self ):
    return self._dim

  @dim.setter
  def dim( self, aValue ):
    self._dim = aValue
    print(self._dim)

  def _nextdim( self ):
    '''  '''
    self._dim += 0x7F
    if self._dim > 0xFF :
      self._dim = 0

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
  def hhmm( self ):
    '''Get "hh:mm" in string format (for the settings http server).'''
    return Clock.tmconvert.format(self._h, self._m)

  @hhmm.setter
  def hhmm( self, aValue ):
    '''todo: Convert "hh:mm" into hours/minutes and set the time.'''
    pass

  @property
  def date( self ):
    '''Get "yy-mm-dd" in string format (for the settings http server).'''
    t = datetime.date.today()
    return Clock.dtconvert.format(t.year, t.month, t.day)

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
    c = int(aValue[1:], 16) #skin the leading #
    self._color = c

  @property
  def location( self ):
    '''Get the location zip.'''
    return self._location

  @location.setter
  def location( self, aLoc ):
    '''Set the location zip and setup the querry url for the weather update thread.'''
    self._location = aLoc

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
    with open(Clock.fname, 'w+') as f:
      data = {}
      data['tempon'] = self.tempdisplay
      data['tempduration'] = self.tempdisplaytime
      data['interval'] = self.tempdisplayinterval
      data['update'] = self.tempupdateinterval
      data['location'] = self.location
      data['color'] = self.colorstr
      data['alarm'] = self.alarmhhmm
      data['alarmon'] = self.alarmenabled
      data['alwayson'] = self.alwaysontimes
      data['dim'] = self.dim

      dump(data, f)

  def load( self ):
    '''Load options from json file.'''
    try:
      with open(Clock.fname, 'r') as f:
        data = load(f)
        self.tempdisplay = data['tempon']
        self.tempdisplayinterval = data['interval']
        self.tempdisplaytime = data['tempduration']
        self.tempupdateinterval = data['update']
        self.colorstr = data['color']
        self.location = data['location']
        self.alarmhhmm = data['alarm']
        self.alarmenabled = data['alarmon']
        self.alwaysontimes = data['alwayson']
        self.dim = data['dim']
    except:
      pass

  def char( self, aPos, aChar, aOn, aFont ):
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
      for c in charA:
        py = aPos[1]
        for r in range(fonth):
          if c & 0x01:
            pygame.draw.line(self.screen, self._color, (px, py), (px, py))
          py += 1
          c >>= 1
        px += 1

  def drawtext( self, aPos, aString, aOn, aFont ):
    '''Draw a text at the given position.  If the string reaches the end of the
       display it is wrapped to aPos[0] on the next line.  aSize may be an integer
       which will size the font uniformly on w,h or a or any type that may be
       indexed with [0] or [1].'''

    if aFont == None:
      return

    px, py = aPos
    width = aFont["Width"] + 1
    for c in aString:
      self.char((px, py), c, aOn, aFont)
      px += width
      #We check > rather than >= to let the right (blank) edge of the
      # character print off the right of the screen.
      if px + width > self.size[0]:
        py += aFont["Height"] + 1
        px = aPos[0]

  def iline( self, sx, sy, ex, ey ):
    '''Draw a line from sx,sy to ex,ey.'''
    pygame.draw.line(self.screen, self._color, (sx, sy), (ex, ey))

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
    for s in seglist:
      self.drawseg(pos, Clock.segs[s], wh)

  def draw( self ):
    '''Draw the display.'''
    self.screen.fill(0x000000)
    x, y = self.pos

    #Draw an hour or minute digit.
    def drawdig( anum, avalue ):
      p = (x + int(self.wh * Clock.digitpos[anum]), y)
      self.drawsegs(p, Clock.nums[avalue], self.wh)

    #Draw am or pm depending on the hour.
    def drawapm( anum, avalue ):
      wh = self.wh // 2
      p = (x + int(self.wh * Clock.digitpos[anum]), y)
      self.drawsegs(p, Clock.apm[avalue], wh)
      if avalue < 2:
        p = (p[0] + wh + (wh // 2) + 1, y)
        self.drawsegs(p, Clock.apm[2], wh)

    #Draw hh, mm and am/pm.
    for x in range(4):
      drawdig(x, self.digits[x])
    drawapm(4, self.digits[4])

    #If alarm enabled print the bell icon.
    if self._alarmenabled:
      p = (x + int(self.wh * Clock.digitpos[4]), y + 4 + self.wh)
      self.char(p, '\x1F', True, terminalfont)

    #If we want to display the temperature then do so at the bottom right.
    if self.tempdisplay:
      p = (x + int(self.wh * Clock.digitpos[4]), y + 3 + (self.wh * 2))
      wh = Clock.tempsize
      n0 = (self.temp // 100) % 10
      n1 = (self.temp // 10) % 10
      n2 = self.temp % 10
      #Don't draw hundreds location unless it's not 0.
      if n0:
        ph = (p[0] - wh - 2, p[1])
        self.drawsegs(ph, Clock.nums[n0], wh)
      self.drawsegs(p, Clock.nums[n1], wh)
      p = (p[0] + wh + 2, p[1])
      self.drawsegs(p, Clock.nums[n2], wh)
      p = (p[0] + wh + 4, p[1])
      self.drawsegs(p, Clock.apm[3], wh)

    def drawrect(pos):
      rect = (pos[0], pos[1], 3, 3)
      pygame.draw.rect(self.screen, self._color, rect)

    drawtext = self._tab == 0

    #Draw the colon in between hh and mm every second for a second.
    #This will cause it to blink.
    if self.digits[5] & 1:
      sx = (Clock.digitpos[1] + 1.0 + Clock.digitpos[2]) / 2
      sy = (self.wh // 3) * 2
      p = (int(sx * self.wh) + x, y + sy)
      drawrect(p)
      sy += sy
      p = (p[0], y + sy)
      drawrect(p)

      drawtext = True

    if drawtext and Clock._tabname[self._tab] != '':
        p = (x, y + 10 + (self.wh * 2))
        self.drawtext(p, Clock._tabname[self._tab], True, terminalfont)

  def UpdateWeather( self ):
    '''Update weather by reading it from weather.com.'''
    try:
      self.temp, self.text = weather.get(self.location)
      #Limit the condition string to max length.
      if len(self.text) > Clock._conditionlen:
        self.text = self.text[:Clock._conditionlen]
      Clock._tabname[0] = self.text
      #todo: clamp text to maximum size.
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

  def Update( self, dt ):
    '''Run update of face check, time and display state.'''

    self.processalarmbutton()
    state = self._buttons[Clock.alarmonoff].update()
    if state == button.CHANGE:
      self.alarmenabled = not self.alarmenabled

    t = time.localtime()
    self._curtime = (t.tm_hour, t.tm_min)
    s = t.tm_sec

    apm = 0

    #Update button pressed states.
    tbuttonstate = self._buttons[Clock.timeset].update()
    msetstate = self._buttons[Clock.minuteset].update()

    if self._tab == 0:
      #Minute button updates dimness.
      if msetstate == button.CHANGE :
        self._nextdim()

      h, m = self._curtime                      #Display current time.

      #Update temp and display temp in main display if it's time.
      if self.tempdisplay:
        #If timeset button is pressed during regular display we trigger temp update.
        if self._buttons[Clock.timeset].pressed:
          self.triggerweatherupdate()

        #If time to display then do so.
        if ((s % self.tempdisplayinterval) < self.tempdisplaytime):
          h = self.temp // 100                  #Clear hours to 0.
          m = self.temp % 100                   #Set minutes to the temperature (only works for positive temps).
          apm = 3                               #Set am/pm to deg symbol.
    elif self._tab == 4:
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
    else:
      if self._tab == 1:
        h, m = self._alarmtime
      elif self._tab == 2:
        m = self.alwaysontimes[0]
        h = m // 60
        m = m % 60
      elif self._tab == 3:
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
        state = self._buttons[Clock.hourset].update()
        #If hourset pressed then increase hour.
        if button.ison(state) and self.checkinc(state, Clock.incrateh, dt):
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

    self.digits = (h // 10, h % 10, m // 10, m % 10, apm, s)

    #Don't update alarm while we are setting it.
    if self._tab != 1:
      self.UpdateAlarm(dt)

  def run( self ):
    '''Run the clock.'''
    self._wtthread.start()
    self._settingsthread.start()

    while self._running:
      ct = time.time()
      dt = min(1.0, ct - self._prevtime) #clamp max elapsed time to 1 second.
      self._prevtime = ct

      self.Update(dt)
      self.clock.tick(60)
      self.draw()

      for event in pygame.event.get():
        if event.type == QUIT:
          self._running = False
          break
        elif event.type == KEYDOWN:
          if event.key == K_t:
            self.wh += 1
          elif event.key == K_r:
            self.wh -= 1
            if (self.wh < 0):
              self.wh = 0

      pygame.display.update()

    self.save()                                 #Save current settings.
    pygame.display.quit()
    print("Shutting down threads.")
    self._wtthread.join()
    self._settingsthread.join()

def run(  ):
  clk = Clock()
  clk.run()

if __name__ == '__main__':
  run()
