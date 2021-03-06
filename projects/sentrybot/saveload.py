#!/usr/bin/env python3
#11/10/2018 11:10 AM

from json import dump, load
from sound import *
from gamepad import *
from body import saveparts, loadparts

savename = 'options.json'

def jsonsounddata( aSource ):
  '''Convert the map of evdev button ids: sound objects to
      list of (button name, group #, filename) entries'''
  dest = []
  for btn, snds in aSource.items():
    peace, combat = snds
    if peace != None or combat != None:
      name = gamepad.btntoname(btn)
      if name != None:
        pfilename = peace.filename if peace != None else ""
        cfilename = combat.filename if combat != None else ""
        dest.append((name, peace.group, pfilename, cfilename))

  return dest

def saveproperties( bot ):
  '''Save options to json file.'''
  try:
    data = {}
    data['controller'] = bot.controllernum
    data['armangle'] = bot.armangle
    data['rate'] = bot.rate
    data['startup'] = bot.startupsound.filename if bot.startupsound else None
    data['gun'] = bot._gunsfx
    data['gunrate'] = bot.gunrate
    data['macaddress'] = bot.macaddress         #Mac address for the 8Bitdo gamepad.

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

def doset( bot, data ):
  bot.controllernum = data['controller']
  bot.armangle = data['armangle']
  bot.rate = data['rate']
  bot.startupsound = data['startup']
  bot.initsounds(data['sounds'])
  bot._gunsfx = data['gun']
  bot.gunrate = data['gunrate']
  bot.macaddress = data['macaddress']
  loadparts(data)                           #Load body part data from json.
  bot.setspeeds(data['speeds'])

def loadproperties( bot ):
  '''Load options from json file.'''
  try:
    with open(savename, 'r') as f:
      data = load(f)
      doset(bot, data)
  except Exception as e:
    print('option load error:', e)

def loadpropertiesfromstring( bot, astring ):
  try:
    data = loads(astring)
    doset(bot, data)
  except Exception as e:
    print('option load error:', e)

#------------------------------------------------------------------------
if __name__ == '__main__':  #start server and open browser
  savename = 'test.json'
  class testsnd(object):
    '''This is all testing support objects.'''
    def __init__( self, aGroup, aFile ):
      self.group = aGroup
      self.filename = aFile

  class testobj(object):

    buttonsounds = {
      ecodes.BTN_A : [testsnd(1, 'alertsafety'), None],
      ecodes.BTN_B : [testsnd(1, 'alertsecurity'), None],
      ecodes.BTN_C : [testsnd(1, 'allcitizenscalm'), None],
      ecodes.BTN_X : [testsnd(1, 'donotinterfere'), None],
      ecodes.BTN_Y : [testsnd(1, 'hostiledetected2'), None],
      ecodes.BTN_SELECT : [testsnd(1, 'hostiles'), None],
      ecodes.BTN_START : [testsnd(1, 'movealong'), None],
      ecodes.BTN_TL2 : [testsnd(1, 'nohostiles'), None],
      ecodes.BTN_TR2 : [testsnd(1, 'noncombatants'), testsnd(1, 'privateproperty')],
      ecodes.BTN_TL : [testsnd(1, 'privateproperty'), None],
      ecodes.BTN_TR : [testsnd(1, 'systemreport'), None],
      ecodes.BTN_THUMBL : [testsnd(1, 'warningleave'), None],
      ecodes.BTN_THUMBR : [testsnd(1, 'warningsecurity'), None],
      gamepad.BTN_DPADU : [testsnd(2, 'warningviolation'), None],
      gamepad.BTN_DPADR : [testsnd(2, 'weaponsfree'), None],
      gamepad.BTN_DPADD : [testsnd(2, 'weaponslocked'), None],
      gamepad.BTN_DPADL : [testsnd(2, 'startup'), None],
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

