#!/usr/bin/env python3
#11/15/2018 11:37 PM

from pca9865 import *
from quicrun import *
from gamepad import *
from sound import *
from settings import *
from buttons import gpioinit, button
from kivy.clock import Clock
from kivy.base import EventLoop

import angle
import body
import saveload
import ps2con
import legs
import RPi.GPIO as GPIO

from threading import Thread #,Lock
from time import perf_counter, sleep
import keyboard

gpioinit() #Initialize the GPIO system so we may use the pins for I/O.

def deadzone( aValue, aLimit ):
  return aValue if abs(aValue) >= 0.01 else 0.0

_dtime = .03
_startupswitch = button(26)

#Sound Channels
#0 = idle
#1 = voices
#2 = body
#3 = gun

#------------------------------------------------------------------------
class sentrybot(object):

  _PEACE, _COMBAT = range(2)

  #map of button to sound object.  This is loaded from a json file.
  #1st sound is for peacful stance, 2nd is combat stance.
  _buttonsounds = {
    ecodes.BTN_A : [None, None],
    ecodes.BTN_B : [None, None],
    ecodes.BTN_C : [None, None],
    ecodes.BTN_X : [None, None],
    ecodes.BTN_Y : [None, None],
    ecodes.BTN_SELECT : [None, None],
    ecodes.BTN_START : [None, None],
    ecodes.BTN_TL2 : [None, None],
    ecodes.BTN_TR2 : [None, None],
    ecodes.BTN_TL : [None, None],
    ecodes.BTN_TR : [None, None],
    ecodes.BTN_THUMBL : [None, None],
    ecodes.BTN_THUMBR : [None, None],
    gamepad.BTN_DPADU : [None, None],
    gamepad.BTN_DPADR : [None, None],
    gamepad.BTN_DPADD : [None, None],
    gamepad.BTN_DPADL : [None, None]
  }

  #map of ps2 cotnroller buttons to 8Bitdo FC30 Pro retro controller buttons.
  _ps2map = {
    ps2con.CIRCLE : ecodes.BTN_A,
    ps2con.CROSS : ecodes.BTN_B,
    ps2con.TRIANGLE : ecodes.BTN_X,
    ps2con.SQUARE : ecodes.BTN_Y,
    ps2con.SELECT : ecodes.BTN_SELECT,
    ps2con.START : ecodes.BTN_START,
    ps2con.L_TRIGGER : ecodes.BTN_TL2,
    ps2con.R_TRIGGER : ecodes.BTN_TR2,
    ps2con.L_SHOULDER : ecodes.BTN_TL,
    ps2con.R_SHOULDER : ecodes.BTN_TR,
    ps2con.L_HAT : ecodes.BTN_THUMBL,
    ps2con.R_HAT : ecodes.BTN_THUMBR,
    ps2con.DPAD_U : gamepad.BTN_DPADU,
    ps2con.DPAD_R : gamepad.BTN_DPADR,
    ps2con.DPAD_D : gamepad.BTN_DPADD,
    ps2con.DPAD_L : gamepad.BTN_DPADL
  }

  #PS2 joystick is RX, RY, LX, LY while gamepad is LX, LY, RX, RY.
  _ps2joymap = (ps2con.LX, ps2con.LY, ps2con.RX, ps2con.RY)

  _MACHINEGROUP = 20                            #Sound group for machine sounds.
  _speeds = (.25, .5, 1.0)
  _startupsfx = 'sys/startup'
  _gunsfx = 'sys/gun2'
  _combatsfx = 'sys/equipcombat'
  _speedsounds = ('sys/one', 'sys/two', 'sys/three', 'sys/four', 'sys/five', 'sys/six')
  _headlightindex = 14                          #Servo controller index for head LED.
  _SMOKEPIN = 20
#  _laser = 12
#  _GUNBUTTON = 26                               #GPIO # for button pin.

  def __init__( self ):
    sound.setdefaultcallback(self._sounddone)

    self._stance = sentrybot._PEACE             #The combat stance used for animation and sound picking.
    self._controllernum = 0                     #Type of controller 0=FC30, 1=ps2
    self._controller = None                     #Start out with no controller. Will set once we no which type.
    self._startupsound = None
    self._gunsound = [None, None]
#    self._gunbutton = button(sentrybot._GUNBUTTON)
    self._rotx = 0.0                            #Arm/body/head rotation x.
    self._roty = 0.0                            #Arm/head rotation y.
    self._rate = 90.0                           #Maximum rate of rotation in degs/second.
    self._speed = 0                             #Start at lowest speed setting.
    self._speedchange = 0                       #Value to indicate speed "gear" has changed.
    self._recording = False                     #Flag indicating we are recording input for animation playback.
    self._hy = 0.0                              #Head y value converting button presses into +/- joystick type value.
    self._gpmacaddress = '' #'E4:17:D8:2C:08:68'
    self.armangle = 0.0                         #Angle of arms used to rotate x,y input to the 2 arm servos.
    self.invert = False                         #Invert joystick y input.
    self._pca = pca9865(100)
    self._buttonpressed = set()                 #set used to hold button pressed states, used for debounce detection.
    self._gunrate = 0.15
    self._gunon = False
    self._gunindex = 0
    self._armson = True

#Put these in to turn on the head laser.
#    GPIO.setup(sentrybot._laser, GPIO.OUT)
#    GPIO.output(sentrybot._laser, GPIO.HIGH)
    GPIO.setup(sentrybot._SMOKEPIN, GPIO.OUT)

    self.load()                                 #load settings json

    #If no keyboard we'll get an exception here so turn off keyboard flag.
    try:
      bres = keyboard.is_pressed('q')
      self._haskeyboard = True
    except:
      self._haskeyboard = False

    self._running = True

    sound.start()                               #Start the sound event listener
    self._idle = sound('idle', 0)
    self._idle.loop = True
    self._idle.volume = 0.05
    self._idle.keeploaded = True
    self._idle.load()

    self._torsosound = sound('torso2', 2)
    self._torsosound.volume = 0.1
    self._torsosound.keeploaded = True
    self._torsosound.load()
    self._torsodir = 0.0

    self._smokes = body.speedpart(self._pca, 13, 'smoke')

    #Start settings server, 2nd param True if testing html page.
    self._settingsthread = Thread(target=lambda: settings.run(self, True))

  def __del__( self ):
    self.save()
    self._contoller = None

  @property
  def macaddress( self ):
    return self._gpmacaddress

  @macaddress.setter
  def macaddress( self, aValue ):
    self._gpmacaddress = aValue
    if self.controllernum == 0 and self._controller != None:
      self._controller.macaddress = aValue

  @property
  def recording( self ):
    return self._recording

  @recording.setter
  def recording( self, aValue ):
    self._recording = aValue
    #todo: Create/Kill the recorder?

  @property
  def gunrate( self ):
    return self._gunrate

  @gunrate.setter
  def gunrate( self, aValue ):
    self._gunrate = aValue

  @property
  def optionsfile( self ): return saveload.savename

  @property
  def partdata( self ): return body._initdata

  @property
  def running( self ): return self._running

  @property
  def stance( self ):
    return self._stance

  @stance.setter
  def stance( self, aValue ):
    self._stance = aValue

  @property
  def rate( self ):
    return self._rate

  @rate.setter
  def rate( self, aValue ):
    self._rate = aValue

  @property
  def buttonsounds( self ):
    return sentrybot._buttonsounds

  def getsound( self, aButton ):
    '''Get sound assigned to given button and curent stance.'''
    return sentrybot._buttonsounds[aButton][self._stance]

  def setsound( self, aButton, aStance, aSound ):
    '''Set sound for button.  If aStance < 0 then current stance is used. '''
    s = self._stance if aStance < 0 else aStance
    sentrybot._buttonsounds[aButton][s] = aSound

  @property
  def startupsound( self ):
    return self._startupsound

  @startupsound.setter
  def startupsound( self, aFile ):
    if aFile != None:
      aFile = sound(aFile) if (aFile != 'None') else None
    self._startupsound = aFile

  @property
  def armangle( self ):
    return self._armangle

  @armangle.setter
  def armangle( self, aValue ):
    '''Set the arm angle, then set the cos/sin values and arm x,y limits.'''
    self._armangle = aValue
    self._cossinl = angle.cossin(aValue)
    #Note: Negate aValue for my stuff.  The Sentrybot doesn't use it.
    self._cossinr = angle.cossin(aValue)
    #Calc the arm x,y ranges.  This is assuming max rotation limits.
    self._armx, self._army = angle.calcbounds(aValue, (-90.0, 90.0), (-90.0, 90.0))

  @property
  def invert( self ):
    return self._invert > 0.0

  @invert.setter
  def invert( self, aValue ):
    self._invert = -1.0 if aValue else 1.0

  def btntoname( self, aButton ):
    '''Abstraction interface for access to gamepad.btntoname()'''
    return gamepad.btntoname(aButton)

  def previewsound( self, aFile ):
    #NOTE: May need to kick this off in the main thread and just queue it here.
    snd = sound(aFile, 10)             #Group 10.
    snd.play()

  def setbuttonsound( self, aButton, aStance, aFile ):
    '''Assign given sound by name to given button name/stance.'''

    #NOTE: We create a new sound object for each call.
    # But if the same file is used for multiple buttons we
    # don't use the same sound object. Not worrying about that
    # because each button should be assigned a different sound anyway.
    if aButton == 'startup':
#      print('setting startup to', aFile)
      self.startupsound = aFile
    else:
      btnnum = gamepad.nametobtn(aButton)
      if aFile:
        aFile = sound(aFile) if (aFile != 'None') else None
      self.setsound(btnnum, aStance, aFile)

  @property
  def controllernum( self ): return self._controllernum

  @controllernum.setter
  def controllernum( self, aValue ):
    '''Set the controller #.'''
    self._controllernum = aValue
#    print('Controller:', self._controllernum)

  def _initcontroller( self ):
    '''Create the controller if necessary.'''
    if self._controllernum:
#      print('starting ps2 controller')
      self._controller = ps2con.ps2con(27, 22, 18, 17, self._ps2action)
    else:
#      print('starting Retro Controller')
      self._controller = gamepad(self.macaddress, self._buttonaction)

  def setcontroller( self, aIndex ):
    '''Set controller index if it changed, and create a controller.'''
    if self.controllernum != aIndex or self._controller == None:
      self.controllernum = aIndex
      self._initcontroller()

  def trypair( self ):
    '''If 8Bitdo controller is selected and it's not connected, attempt a pairing.'''
    if self.controllernum == 0 and self._controller != None and self._controller.connected == False:
      self._controller.pair()

  def initsounds( self, aSounds ):
    '''Temporary method to initialize sounds from a list of button, group, sound'''
    for s in aSounds:
      b = gamepad.nametobtn(s[0])               #Turn button name into button #.
      def setit(aStance):
        sname = s[2 + aStance]
        if sname != "":
          self.setsound(b, aStance, sound(sname, s[1]))
        else:
          self.setsound(b, aStance, None)

      if b >= 0:
        setit(sentrybot._PEACE)
        setit(sentrybot._COMBAT)

    #Initialize other sounds here.
    for i in range(2):
      self._gunsound[i] = sound(sentrybot._gunsfx, 3)
      self._gunsound[i].keeploaded = True
      self._gunsound[i].load()

  def _sounddone( self, aSound ):
    '''Callback function when sound file is done playing.'''
    #NOTE: This does nothing, but it it's not set, we don't get events at all, and sound looping and stoping events
    #  will not process.
#    print('Done:', aSound.source)
    pass

  def checktorso( self, x ):
    '''  '''
    if x != 0.0:
      rx = self._torsodir * x
      if rx < 0.0 or self._torsodir == 0.0:
        s = sound.groupplaying(self._torsosound.group)
        if s == None or s == self._torsosound:
          self._torsosound.stop()
          self._torsosound.play()

    self._torsodir = x

  def partrate( self, aIndex ):
    '''Get rate for given part.'''
    p = body.getpart(aIndex)
    return p.rate if p else 0.0

  def partcenter( self, aIndex ):
    '''Get rate for given part.'''
    p = body.getpart(aIndex)
    return p.center if p else 0.0

  def partminmax( self, aIndex ):
    '''Get min/max for given part.'''
    p = body.getpart(aIndex)
    return p.minmax if p else (0.0, 100.0)

  def partdefminmax( self, aIndex ):
    '''Get min/max for given part.'''
    p = body.getpart(aIndex)
    return p._defminmax if p else (-100.0, 100.0)

  def setpartdata( self, aIndex, aRate, aTrim, aMinMax ):
    '''Set the rate, trim and min/max values for given part.'''
    p = body.getpart(aIndex)
    if p:
      p.rate = aRate
      p.center = aTrim
      p.minmax = aMinMax

  def save( self ):
    '''Do save of properites.'''
    saveload.saveproperties(self)

  def load( self ):
    '''Do load of properties.'''
    saveload.loadproperties(self)

  def loadfromstring( self, aString ):
    '''Load properties from given string.'''
    saveload.loadpropertiesfromstring(self, aString)

  def _initparts( self ):
    '''Initialize all of the parts.'''
    body.initparts(self._pca)
    self._setspeed()

  def _center( self ):
    self._rotx = 0.0
    self._roty = 0.0

  def brake( self, abTF ):
    '''Brake the legs.'''
    lleg = body.getpart(body._LLEG)
    rleg = body.getpart(body._RLEG)
    lleg.brake(abTF)
    rleg.brake(abTF)

  def _fire( self, abTF ):
    '''Fire gun by setting motor speed to 100%, stop by setting to 0%.'''
    p = body.getpart(body._GUN)
    p.value = p.minmax[abTF]
    #Turn smoke generator on/off.
    GPIO.output(sentrybot._SMOKEPIN, GPIO.HIGH if abTF else GPIO.LOW)
    self._gunon = abTF
    self._guntime = 0.0
    self._smokes.value = 50.0 if abTF else 0.0

  def getspeeds( self ):
    '''Get tuple of speeds as comma separated string.'''
    return ', '.join(str(s) for s in sentrybot._speeds)

  def setspeeds( self, aSpeeds ):
    '''Set tuple of speeds from comma separated string.'''
    spds = aSpeeds.split(',')
#    print(spds)
    try:
      sentrybot._speeds = tuple(float(s) for s in spds)
    except Exception as e:
      #On error we print the exception and continue with default speed values.
      print(e)

  def _setspeed( self ):
    '''Set the speed scale value on the legs to the current _speed setting.'''
    lleg = body.getpart(body._LLEG)
    rleg = body.getpart(body._RLEG)
    lleg.scale = rleg.scale = sentrybot._speeds[self._speed]

  def _nextspeed( self ):
    '''Increment to the next speed.'''
    self._speedchange += 2 #This will make it 4.  Used to determine debounce actions.
    self._speed += 1
    if self._speed >= len(sentrybot._speeds):
      self._speed = 0

#    print('speed:', self._speed)

    #Play corresponding sound.
    if self._speed < len(sentrybot._speedsounds):
      snd = sound(sentrybot._speedsounds[self._speed], 1)
      snd.play()
    self._setspeed()

  def _joy( self, aIndex ):
    '''Get joystick value in range -1.0 to 1.0'''

    #PS2 controller has different stick mappings.
    if self._controllernum == 1:
      aIndex = sentrybot._ps2joymap[aIndex & 0x03]  #Make sure value is in range.

    return self._controller.getjoy(aIndex) / 255.0

  def _togglearms( self ):
    '''Toggle arms servos on/off.'''
    if self._armson:
      def turnoff( apart ):
        part = body.getpart(apart)
        part.off()

      turnoff(body._RARM_H)
      turnoff(body._RARM_V)
      turnoff(body._LARM_H)
      turnoff(body._LARM_V)
      self._armson = False
    else:
      self._center()
      self._armson = True

  def _togglecombat( self ):
    '''Toggle combat stance.'''

    self._stance = 1 - self._stance
    p = body.getpart(body._MISSILES)
    if self._stance == sentrybot._COMBAT:
#      s = soundchain((sentrybot._combatsfx, 'engaging'), sentrybot._MACHINEGROUP)
      s = sound(sentrybot._combatsfx, sentrybot._MACHINEGROUP)
      s.play()
      p.value = p.minmax[1]
    else:
      p.value = 0.0
      s = soundchain(('sys/six',
                      'sys/five',
                      'sys/four',
                      'sys/three',
                      'sys/two',
                      'sys/one'), sentrybot._MACHINEGROUP)
      s.play()

  def _ps2action( self, aButton, aValue ):
    '''Callback for ps2 button events. They are remapped to FC30 events and sent
       to the _buttonaction callback.'''
#    print('Action:', aButton, aValue)
    #Value of 2 indicates a change in pressed/released state.
    if aValue & 0x02:
      k = sentrybot._ps2map[aButton]
#     print(aButton, aValue, k)
      self._buttonaction(k, aValue)

  def _buttonaction( self, aButton, aValue ):
    '''Callback function for 8Bitdo FC30 Pro controller.'''

#    print('Button:', gamepad.btntoname(aButton), aValue)

    #If button pressed
    if aValue & 0x01:
      self._buttonpressed.add(aButton)
      if aButton == ecodes.BTN_THUMBL:
        self.brake(True)
        self._buttonpressed.remove(aButton)
      if aButton == ecodes.BTN_TL2:
        self._hy += 1.0
      elif aButton == ecodes.BTN_TR2:
        self._hy -= 1.0
      elif aButton == ecodes.BTN_B:
#        print('fire')
        self._fire(True)
      else: #We now check for button combos.
        processed = False #When set to true we processed the button event so stop checking for other button combos.
        if aButton == ecodes.BTN_START or aButton == ecodes.BTN_SELECT:
          chk = ecodes.BTN_SELECT if aButton == ecodes.BTN_START else ecodes.BTN_START
          if chk in self._buttonpressed:
#            print('SELECT + START')
            self._nextspeed()

            #Remove these buttons from pressed list so we don't play sound on release.
            self._buttonpressed.remove(chk)
            self._buttonpressed.remove(aButton)
            processed = True
        if not processed and (aButton == ecodes.BTN_TL or aButton == ecodes.BTN_TR):
          chk = ecodes.BTN_TL if aButton == ecodes.BTN_TR else ecodes.BTN_TR
          if chk in self._buttonpressed:
#            print('TL + TR')
            self._togglecombat()
            self._buttonpressed.remove(chk)
            self._buttonpressed.remove(aButton)
            processed = True
        if not processed and (aButton == ecodes.BTN_Y or aButton == ecodes.BTN_A):
          chk = ecodes.BTN_Y if aButton == ecodes.BTN_A else ecodes.BTN_A
          if chk in self._buttonpressed:
#            print('Y + A')
            self._center()
            self._buttonpressed.remove(chk)
            self._buttonpressed.remove(aButton)
            processed = True
        if (aButton == gamepad.BTN_DPADL or aButton == ecodes.BTN_A):
          chk = gamepad.BTN_DPADL if aButton == ecodes.BTN_A else ecodes.BTN_A
          if chk in self._buttonpressed:
#            print('DPADL + A')
            self._togglearms()
            processed = True
      #todo: Check for dpadl, A, L_SH and R_SH for animation toggle.
    elif aButton == gamepad.GAMEPAD_DISCONNECT:
      body.off()
      print('Disconnected controller!')
    else: #Handle release events.
      if self.recording:
        #todo: send action to animation recorder.
        pass

      if aButton == ecodes.BTN_THUMBL:
        self.brake(False)
      elif aButton == ecodes.BTN_TL2:
        self._hy -= 1.0
      elif aButton == ecodes.BTN_TR2:
        self._hy += 1.0
      elif aButton == ecodes.BTN_B:
#        print('stopfire')
        self._fire(False)
      else:
        #If we recorded a button press and it wasn't consumed, then play sound on release.
        if aButton in self._buttonpressed:
          s = self.getsound(aButton)
          if s != None:
            self._torsosound.stop()
            s.play()
#            print('playing', s.source)

      #On release, make sure to remove button from pressed state set.
      if aButton in self._buttonpressed:
        self._buttonpressed.remove(aButton)

  def clamparms( self, aX, aY ):
    '''Set arm clamp values.'''
    aX = min(max(self._armx[0], aX), self._armx[1])
    aY = min(max(self._army[0], aY), self._army[1])
    return (aX, aY)

  def _updateparts( self, aDelta ):
    '''Update all servos based on joystick input'''

    rx = -self._joy(gamepad._RX)                #Negate cuz servo is backwards.
    ry = self._joy(gamepad._RY)

    rx = deadzone(rx, 0.01)

    self.checktorso(rx)

    ry = deadzone(ry, 0.01)

    lx = self._joy(gamepad._LX)
    ly = self._joy(gamepad._LY)

    lx = deadzone(lx, 0.01)
    ly = deadzone(ly, 0.01)

    '''
      rx = head, torso, arm horizontal
      ry = right wheel front/back
      lx = Nothing at the moment
      ly = left wheel front/back
    '''

    #If we have a change limit, then use it.
    if self._rate > 0.0:
      if aDelta != 0.0:
        d = self._rate * aDelta
        v = self._rotx + (rx * d)
        self._rotx = min(max(v, -90.0), 90.0)
        v = self._roty + (self._hy * d)           #Use _hy, which is adjusted by l/r triggers.
        self._roty = min(max(v, -90.0), 90.0)
    else:
      v = rx * 90.0
      self._rotx = min(max(v, -90.0), 90.0)
      v = self._hy * 90.0
      self._roty = min(max(v, -90.0), 90.0)

#    print(self._rotx, self._roty, '                ', end='\r')
#    print(rx, ry, '                ', end='\r')

    #todo: Figure out how to disperse right stick movement into torso, head and arms.

    t = body.getpart(body._TORSO)
    v = self._rotx / 8.0
    t.value = v
    hh = body.getpart(body._HEAD_H)
    v =-self._rotx / 4.0
    hh.value = v
    hv = body.getpart(body._HEAD_V)
    hv.value = self._roty

    #Only update arms if they are on.  We can turn them off to keep them from overheating.
    if self._armson:
      rarmh = body.getpart(body._RARM_H)
      rarmv = body.getpart(body._RARM_V)
      larmh = body.getpart(body._LARM_H)
      larmv = body.getpart(body._LARM_V)

#     clampedxy = self.clamparms(self._rotx, self._roty)

      #Rotate x,y by angle and apply to arms.
      armx, army = angle.rotate((self._rotx, self._roty), self._cossinl)
      larmh.value = armx
      larmv.value = army

      larmh.update(aDelta)
      larmv.update(aDelta)

#     clampedxy = self.clamparms(self._rotx, -self._roty)

      #Note, to invert the right arm use _cossinr.
      armx, army = angle.rotate((self._rotx, -self._roty), self._cossinr)
      rarmh.value = armx
      rarmv.value = army

      rarmh.update(aDelta)
      rarmv.update(aDelta)

    lleg = body.getpart(body._LLEG)
    rleg = body.getpart(body._RLEG)

    lleg.speed = ly * lleg.maxspeed
    rleg.speed = ry * rleg.maxspeed

    lleg.update(aDelta)
    rleg.update(aDelta)

#    self._gunbutton.update()
#    if self._gunbutton.pressed:
#      self._gunindex = 1 - self._gunindex
#      self._gunsound[self._gunindex].stop()     #Make sure sound is stopped so we can play it again.
#      self._gunsound[self._gunindex].play()

    g = body.getpart(body._GUN)
    g.update(aDelta)

    #Now play gun sound if gun is on.
    if self._gunon:
      self._guntime -= aDelta
      if self._guntime <= 0.0:
        self._gunindex = 1 - self._gunindex
        self._gunsound[self._gunindex].stop()                     #Make sure sound is stopped so we can play it again.
        self._gunsound[self._gunindex].play()
        self._guntime = self._gunrate

    m = body.getpart(body._MISSILES)
    m.update(aDelta)

  def run( self ):
    '''Main loop to run the robot.'''
    startsfx = sound(sentrybot._startupsfx, sentrybot._MACHINEGROUP)
    startsfx.play()

    if self.startupsound != None:
      def doit():
        self.startupsound.play()
#        self._idle.play()

      Clock.schedule_once(lambda x: doit(), 2.0)

    try:
      self._settingsthread.start()

      #Save init of parts and controller until last second to ensure
      # they get updates as quickly as possible after update.
      self._initparts()
      self._initcontroller()

      prevtime = perf_counter()
      self._pca.set(sentrybot._headlightindex, 550) #550% = 2.2v.

      while self.running:
        if self._haskeyboard and keyboard.is_pressed('q'):
          self._running = False
          print("quitting.")
        else:
          nexttime = perf_counter()
          delta = max(0.001, nexttime - prevtime)
          prevtime = nexttime
          if delta > _dtime:
#            print("Clamping delta: ", delta)
            delta = _dtime

          if self._controller:
            self._controller.update()

          self._updateparts(delta)

          EventLoop.idle()                      #Update kivy event listener

          #Get how much time has passed since beginning of frame and subtract
          # that from the sleep time.
          nexttime = perf_counter()
          sleeptime = _dtime - nexttime - prevtime  #30fps - time we've already wasted.
          if sleeptime > 0.0:
            sleep(sleeptime)

    except Exception as e:
      c = sound('sys/corrupt')                  #Play corruption audio.
      c.play()
      print("Error!")
      raise e
    finally:
      body.off()                                #Make sure motors and servos are off.
      self._idle.stop()

#------------------------------------------------------------------------
if __name__ == '__main__':
  _startupswitch.update()
  #If the startup button is on then start up.
  if len(sys.argv) > 1 or (not _startupswitch.on):
    sentry = sentrybot()
    sentry.run()

