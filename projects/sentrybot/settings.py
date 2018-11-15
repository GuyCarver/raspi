#!/usr/bin/env python3

# Interactive Form for setting clock options.
#.

from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
from string import Template
import time
import cgi
import webbrowser

from os import listdir
from os.path import isfile, join, splitext

settingsfile = ('settings.html', 'advsettings.html', 'log.html')

class settings(BaseHTTPRequestHandler):

  HTML = None                                   #HTML contents loaded for setting.html file.
  testing = False                               #When true HTML file is loaded every get call.
  target = None                                 #Target class to get/set settings on.
  sounddir = 'sounds'                           #Directory to grab sounds from.
  soundFiles = []                               #List of sound files in sounds directory.
  lastsound = None                              #Name of last selected sound in list.
  lastbutton = None                             #Name of last button selected in list.
  lastpart = 0                                  #Index of part currently selected.
  stance = 0                                    #Combat stance for animation and sound.
  page = 0                                      #Settings page #.
  used = {}                                     #Set of used sound names.

  @classmethod
  def determinecontroller( self ):
    #Convert 0, 1 into c_0-1.
    v = 'c_' + str(self.target.controllernum)
#    print('controller is ', v)
    return v

  @classmethod
  def determinepairon( self ):
    '''Return disabled if pair button should not be enabled.'''
    return 'disabled' if self.target.controllernum > 0 else ''

  @classmethod
  def determinestance( self ):
    '''  '''
#    print('getstance:', settings.stance)
    v = 'st_' + str(settings.stance)
    return v

  @classmethod
  def getsoundfiles( self ):
    self.soundFiles = [splitext(f)[0] for f in listdir(self.sounddir) if isfile(join(self.sounddir, f))]
    self.soundFiles.sort()
    self.soundFiles.insert(0, 'None')

  @classmethod
  def getparts( self ):
    curindex = settings.lastpart
    def makeit(index, p):
      selected = ' selected' if index == curindex else ''
      return '<option value="{0}"{1}>{2}</option>'.format(index, selected, p)

    return '\r\n\t'.join([makeit(i, p[0]) for i, p in enumerate(self.target.partdata)])

  @classmethod
  def makesoundlist( self ):
    '''Create html entries for list of sounds. Tag used sounds.'''
    def makeit(f):
      selected = ' selected' if settings.lastsound == f else ''
      #If used set tag.
      if f in self.used:
        tag = 'X: '
      else:
        tag = ''
      return '<option value="{0}"{1}>{2}{0}</option>'.format(f, selected, tag)

    return '\r\n\t'.join([makeit(f) for f in self.soundFiles])

  @classmethod
  def updateused( self ):
    '''Update set of used sound names'''
    self.used = {v[settings.stance].filename for v in self.target.buttonsounds.values() if v[settings.stance] != None }
    #Also add the startup sound.
    v = self.target.startupsound
    if v != None:
      self.used.add(v.filename)

  @classmethod
  def makebuttonlist( self ):
    '''Create list of html entries for buttons by name.'''
    buttonsounds = self.target.buttonsounds
    def makeit(btnname, aSounds):
      s = aSounds[settings.stance]
      if s:
        f = s.filename
        color = ''
      else:
        f = 'None'
        color = ' class="w3-text-gray" '

      selected = ' selected' if settings.lastbutton == btnname else ''

      return '<option {3} value="{0}"{1}>{0} - {2}</option>'.format(btnname, selected, f, color)

    #todo: Sort buttonsounds by btn # before creating list?
    res = [makeit(self.target.btntoname(btn), snd) for btn, snd in buttonsounds.items()]
    res.sort()
#    res.append(makeit('startup', self.target.startupsound))
    return '\r\n'.join(res)

  @classmethod
  def readHTML( self ):
    '''Read HTML content from file.'''
    with open(settingsfile[settings.page], 'r') as f:
      htdata = f.read()
    self.HTML = Template(htdata)

  @classmethod
  def getoptions( self ):
    '''Get options string from the options file.'''
    try:
      with open(self.target.optionsfile, 'r') as f:
        d = f.read()
        return d
    except Exception as e:
      print(e)
      return ''

  @classmethod
  def saveoptions( self, aOptions ):
    '''Load options into target from the given string, then save to file.'''
    self.target.loadfromstring(aOptions)
    self.target.save()

  @classmethod
  def getlog( self ):
    '''  '''
    try:
      with open('sentrybot.log', 'r') as f:
        d = f.read()
        return d
    except Exception as e:
      print(e)
      return ''

  #--------------------------------------------------------------
  def do_GET( self ):  #load initial page
#    print('getting ', self.path)

    #When testing we reload this every get.
    if self.testing:
      self.readHTML()

    if settings.page == 0:
      pmin, pmax = self.target.partminmax(settings.lastpart)
      minv, maxv = self.target.partdefminmax(settings.lastpart)
      ptrim = self.target.partcenter(settings.lastpart)

      subs = { self.determinecontroller() : 'selected',
        'pair_on' : self.determinepairon(),
        'armangle' : self.target.armangle,
        'rate' : self.target.rate,
        'soundlist' : self.makesoundlist(),
        'buttons' : self.makebuttonlist(),
        'parts' : self.getparts(),
        'partrate' : self.target.partrate(settings.lastpart),
        'parttrim' : ptrim,
        'partmin' : pmin,
        'partmax' : pmax,
        'minv' : minv,
        'maxv' : maxv,
        'speeds' : self.target.getspeeds(),
        'macaddr' : self.target.macaddress,
        self.determinestance() : 'selected',
      }
    elif settings.page == 1:
      subs = {
        'options' : self.getoptions()
      }
    else:
      subs = {
        'log' : self.getlog()
      }

    self.send_response(200)
    self.send_header('Content-Type', 'text/html')
    self.end_headers()
    inter = self.HTML.safe_substitute(subs)
    self.wfile.write(bytearray(inter, 'utf-8'))

  #--------------------------------------------------------------
  def do_POST( self ):  #process requests
#    print('Posting')

    #read form data
    form = cgi.FieldStorage(fp = self.rfile, headers = self.headers,
                            environ = {'REQUEST_METHOD':'POST',
                           'CONTENT_TYPE':self.headers['Content-Type']})

    sv = form.getfirst('Save')

    #Read data from forms into variables.
    if settings.page == 0:
      con = form.getfirst('controller')
      armangle = form.getfirst('armangle')
      rate = form.getfirst('rate')
      sb = form.getfirst('Submit')
      pl = form.getfirst('Play')
      pair = form.getfirst('pair')
      setsound = form.getfirst('setsound')
      settings.lastsound = form.getvalue('sound')
      settings.lastbutton = form.getvalue('button')
      settings.stance = int(form.getvalue('stance'))

      if sb != None:
        speeds = form.getfirst('speeds')
        self.target.setspeeds(speeds)

      if pl and self.lastsound:
        if settings.lastsound != 'None':
          self.target.previewsound(self.lastsound)

      if setsound != None:
        if settings.lastbutton and settings.lastsound :
          self.target.setbuttonsound(settings.lastbutton, settings.stance, settings.lastsound)
          self.updateused()

      if pair != None:
        self.target.trypair()

      #if have a target clock write data to it.
      self.target.setcontroller(int(con))
      self.target.armangle = float(armangle)
      self.target.rate = float(rate)

      partrate = form.getfirst('partrate')
      parttrim = form.getfirst('parttrim')
      partmin = form.getfirst('partmin')
      partmax = form.getfirst('partmax')
      self.target.setpartdata(settings.lastpart, float(partrate), float(parttrim), (float(partmin), float(partmax)))

      #After setting value on the previous part, read in new part value.
      settings.lastpart = int(form.getfirst('part'))

      #If save button pressed then save settings to json file.
      if sv != None:
        print('Saving settings.')
        self.target.save()
    elif settings.page == 1:
      if sv != None:
        opts = form.getfirst('options')
        print('Saving options.')
        self.saveoptions(opts)

    page = form.getvalue('setpage')
    if page != None:
      settings.page = int(page)

    self.do_GET()                               #Re-read the data.

  @classmethod
  def init( self, aTarget, aTesting ):
    '''Setup target and testing state.'''
    self.testing = aTesting

    #If not testing we only read HTML file once.
    if not self.testing:
      self.readHTML()

    self.target = aTarget

    self.getsoundfiles()                        #Make list of sound files.
#    print(self.soundFiles)
    self.updateused()

  @classmethod
  def run( self, aTarget, aTesting = False ):
    '''Run the server and loop until target shuts down.'''

    self.init(aTarget, aTesting)

    server = HTTPServer(('', 8080), self)
    server.timeout = 2.0 #handle_request times out after 2 seconds.
  #  print("Starting server")

    #Loop as long as target clock is running or forever if we have none.
    while aTarget.running:
      server.handle_request()
      time.sleep(1.0)

    print('HTTP Server thread exit.')

if __name__ == '__main__':  #Run settings test with dummy data.

  class testsnd(object):
    def __init__( self, aFile ):
      self.filename = aFile

  class testtarget(object):

    _ANGLE = 0
    _MOTOR = 1

    partdata = [
     ("TORSO", 1, _ANGLE, 0.0, 0.0, 90.0),
     ("HEAD_H", 2, _ANGLE, 0.0, 0.0, 90.0),
     ("HEAD_V", 3, _ANGLE, 0.0, 0.0, 30.0),
     ("LARM_H", 4, _ANGLE, 0.0, 0.0, 90.0),
     ("LARM_V", 5, _ANGLE, 0.0, 0.0, 90.0),
     ("RARM_H", 6, _ANGLE, 0.0, 0.0, 90.0),
     ("RARM_V", 7, _ANGLE, 0.0, 0.0, 90.0),
     ("LLEG", 8, _MOTOR, 20.0, 0.0, 20.0),
     ("RLEG", 9, _MOTOR, 20.0, 0.0, 20.0),
     ("GUN", 10, _MOTOR, 75.0, 0.0, 20.0),
    ]

    _buttonnames = {
     'A' : 304,
     'B' : 305,
     'C' : 306,
     'X' : 307,
     'Y' : 308,
     'SELECT' : 309,
     'START' : 310,
     'L_TRIGGER' : 311,
     'R_TRIGGER' : 312,
     'L_SHOULDER' : 313,
     'R_SHOULDER' : 314,
     'L_THUMB' : 315,
     'R_THUMB' : 316,
     'DPAD_U' : 317,
     'DPAD_R' : 318,
     'DPAD_D' : 319,
     'DPAD_L' : 320
    }

    buttonsounds = {
      304 : [testsnd('powerup'), ""],
      305 : [None, ""],
      306 : [None, ""],
      307 : [testsnd('hostiles'), ""],
      308 : [None, ""],
      309 : [None, ""],
      310 : [None, ""],
      311 : [None, ""],
      312 : [None, ""],
      313 : [None, ""],
      314 : [None, ""],
      315 : [None, ""],
      316 : [None, ""],
      317 : [None, ""],
      318 : [None, ""],
      319 : [None, ""],
      320 : [None, ""]
    }

    _speeds = (0.25, 0.5, 1.0)

    optionsfile = 'options.json'
    macaddress = '1:2:3:4'

    @classmethod
    def getspeeds( self ):
      '''  '''
      return ', '.join(str(s) for s in self._speeds)

    @classmethod
    def setspeeds( self, aSpeeds ):
      '''  '''
      spds = aSpeeds.split(',')
      try:
        self._speeds = tuple(float(s) for s in spds)
        print(self._speeds)
      except Exception as e:
        print(e)

    @classmethod
    def partrate( self, aIndex ):
      '''  '''
      return self.partdata[aIndex][3]

    @classmethod
    def partcenter( self, aIndex ):
      return self.partdata[aIndex][4]

    @classmethod
    def partminmax( self, aIndex ):
      '''  '''
      print('part:', self.partdata[aIndex])
      rng = self.partdata[aIndex][5]
      return rng if type(rng) == tuple else (-rng, rng)

    @classmethod
    def partdefminmax( self, aIndex ):
      if aIndex == 9:
        return (0.0, 100.0)
      elif aIndex > 6:
        return (-100.0, 100.0)
      else:
        return (-90.0, 90.0)

    @classmethod
    def setpartdata( self, aIndex, aRate, aTrim, aMinMax ):
      '''  '''
      a, b, c, d, e = self.partdata[aIndex]
      self.partdata[aIndex] = (a, b, c, aRate, aTrim, aMinMax)

    @classmethod
    def nametobtn( self, aValue ):
      '''Get button # of given button name'''
      return self._buttonnames[aValue] if aValue in self._buttonnames else -1

    @classmethod
    def btntoname( self, aButton ):
      '''Get the name given a button value.'''
      for k, v in self._buttonnames.items():
        if v == aButton:
          return k

      return None

    def __init__( self ):
      self.controllernum = 1
      self.armangle = 8.0
      self.rate = 90.0
      self.running = True
      self.startupsound = None

    def previewsound( self, aSound ):
      print("playing sound", aSound)

    def save( self ):
      print('Saving')

    def loadfromstring( self, aString ):
      '''  '''
      print('loading')

    def setcontroller( self, aArg ):
      '''  '''
      self.controller = aArg

    def setbuttonsound( self, aButton, aStatus, aFile ):
      print('Button sound:', aButton, aFile)

      if aFile:
        aFile = testsnd(aFile) if (aFile != 'None') else None

      if aButton == 'startup':
        self.startupsound = aFile
      else:
        btnnum = self.nametobtn(aButton)
        self.buttonsounds[btnnum][aStatus] = aFile

  settings.run(testtarget(), True)
  print('done')

