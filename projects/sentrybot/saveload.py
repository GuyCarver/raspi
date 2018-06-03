#!/usr/bin/env python3

from json import dump, load
from sound import *
from gamepad import *
from body import saveparts, loadparts

savename = 'options.json'

def jsonsounddata( aSource ):
  '''Convert the map of evdev button ids: sound objects to
      list of (button name, group #, filename) entries'''
  dest = []
  for btn, snd in aSource.items():
    if snd != None:
      name = gamepad.btntoname(btn)
      if name != None:
        dest.append((name, snd.group, snd.filename))

  return dest

def saveproperties( bot ):
  '''Save options to json file.'''
  try:
    data = {}
    data['controller'] = bot.controllernum
    data['armangle'] = bot.armangle
    data['rate'] = bot.rate
    data['startup'] = bot.startupsound.filename if bot.startupsound else None

    #Save sound button mappings.
    #Get sounds and convert from:
    # ecode.btn, soundobj to (btnname, group, basefilename)
    data['sounds'] = jsonsounddata(bot.buttonsounds)
    saveparts(data)                           #Save body part data to json.
    data['speeds'] = bot.getspeeds()

    with open(savename, 'w+') as f:
      dump(data, f, indent = 2)
  except Exception as e:
    print('option save error:', e)

def loadproperties( bot ):
  '''Load options from json file.'''
  try:
    with open(savename, 'r') as f:
      data = load(f)
      bot.controllernum = data['controller']
      bot.armangle = data['armangle']
      bot.rate = data['rate']
      bot.startupsound = data['startup']
      bot.initsounds(data['sounds'])
      loadparts(data)                           #Load body part data from json.
      bot.setspeeds(data['speeds'])
  except Exception as e:
    print('option load error:', e)

#------------------------------------------------------------------------
if __name__ == '__main__':  #start server and open browser
  class testsnd(object):
    '''This is all testing support objects.'''
    def __init__( self, aGroup, aFile ):
      self.group = aGroup
      self.filename = aFile

  class testobj(object):

    buttonsounds = {
      ecodes.BTN_A : testsnd(1, 'alertsafety'),
      ecodes.BTN_B : testsnd(1, 'alertsecurity'),
      ecodes.BTN_C : testsnd(1, 'allcitizenscalm'),
      ecodes.BTN_X : testsnd(1, 'donotinterfere'),
      ecodes.BTN_Y : testsnd(1, 'hostiledetected2'),
      ecodes.BTN_SELECT : testsnd(1, 'hostiles'),
      ecodes.BTN_START : testsnd(1, 'movealong'),
      ecodes.BTN_TL2 : testsnd(1, 'nohostiles'),
      ecodes.BTN_TR2 : testsnd(1, 'noncombatants'),
      ecodes.BTN_TL : testsnd(1, 'privateproperty'),
      ecodes.BTN_TR : testsnd(1, 'systemreport'),
      ecodes.BTN_THUMBL : testsnd(1, 'warningleave'),
      ecodes.BTN_THUMBR : testsnd(1, 'warningsecurity'),
      gamepad.BTN_DPADU : testsnd(2, 'warningviolation'),
      gamepad.BTN_DPADR : testsnd(2, 'weaponsfree'),
      gamepad.BTN_DPADD : testsnd(2, 'weaponslocked'),
      gamepad.BTN_DPADL : testsnd(2, 'startup')
    }

    _startupsound = 'powerup'

    def __init__( self, arg ):
      self.controller = arg

    def initsounds( self, aArg ):
      testobj.mysounds = aArg

    @property
    def startupsound( self ):
      return testobj._startupsound

    @startupsound.setter
    def startupsound( self, aValue ):
      testobj._startupsound = aValue

  t = testobj(1)
  print('saving')
  saveproperties(t)

  t.controller = 0
  testobj.mysounds = None

  print('loading')
  loadproperties(t)

  print(t.controller)
  print(testobj.mysounds)

