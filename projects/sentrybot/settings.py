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

class RH(BaseHTTPRequestHandler):

  HTML = None
  testing = False
  target = None                                #Target Clock class.
  sounddir = 'sounds'
  soundFiles = []                               #List of sound files in sounds directory.
  lastsound = None
  lastbutton = None
  used = {}

  @staticmethod
  def determinecontroller(  ):
    v = 'c_' + str(RH.target.controller)
#    print('controller is ', v)
    return v

  @classmethod
  def getsoundfiles( self ):
    self.soundFiles = [splitext(f)[0] for f in listdir(self.sounddir) if isfile(join(self.sounddir, f))]
    self.soundFiles.sort()
    self.soundFiles.insert(0, 'None')

  @classmethod
  def makesoundlist( self ):
    '''Create html entries for list of sounds. Tag used sounds.'''
    def makeit(f):
      selected = ' selected' if self.lastsound == f else ''
      #If used set tag.
      if f in self.used:
        tag = 'X: '
      else:
        tag = ''
      return '<option value="{0}"{1}>{2}{0}</option>'.format(f, selected, tag)

    return '\r\n\t'.join([makeit(f) for f in self.soundFiles])

  @classmethod
  def updateused( self ):
    self.used = {v.filename for v in self.target.buttonsounds.values() if v != None }
    v = self.target.startupsound
    if v != None:
      self.used.add(v.filename)

  @classmethod
  def makebuttonlist( self ):
    buttonsounds = self.target.buttonsounds
    def makeit(btnname, s):
      if s:
        f = s.filename
        color = ''
      else:
        f = 'None'
        color = ' class="w3-text-gray" '

      selected = ' selected' if self.lastbutton == btnname else ''

      return '<option {3} value="{0}"{1}>{0} - {2}</option>'.format(btnname, selected, f, color)

    res = [makeit(self.target.btntoname(btn), snd) for btn, snd in buttonsounds.items()]
    res.sort()
    res.append(makeit('startup', self.target.startupsound))
    return '\r\n'.join(res)

  @classmethod
  def readHTML( self ):
    '''  '''
    with open('settings.html', 'r') as f:
      htdata = f.read()
    self.HTML = Template(htdata)

  #--------------------------------------------------------------
  def do_GET( self ):  #load initial page
    #When testing we reload this every get.
    if self.testing:
      self.readHTML()

#    print('getting ' + self.path)
    subs = { self.determinecontroller() : 'selected',
      'speed' : self.target.speed,
      'accel' : self.target.accel,
      'soundlist' : self.makesoundlist(),
      'buttons' : self.makebuttonlist(),
      'headturn' : self.target.headturnlimit,
    }

    self.send_response(200)
    self.send_header('Content-Type', 'text/html')
    self.end_headers()
    inter = self.HTML.safe_substitute(subs)
    self.wfile.write(bytearray(inter, 'utf-8'))

  #--------------------------------------------------------------
  def do_POST( self ):  #process requests
    #read form data
    form = cgi.FieldStorage(fp = self.rfile, headers = self.headers,
                            environ = {'REQUEST_METHOD':'POST',
                           'CONTENT_TYPE':self.headers['Content-Type']})

    #Read data from forms into variables.
    con = form.getfirst('controller')
    speed = form.getfirst('speed')
    accel = form.getfirst('accel')
    sv = form.getfirst('Save')
    pl = form.getfirst('Play')
    setsound = form.getfirst('setsound')
    headturnlimit = form.getvalue('headturn')
    RH.lastsound = form.getvalue('sound')
    RH.lastbutton = form.getvalue('button')

    if pl and self.lastsound:
      if self.lastsound != 'None':
        self.target.previewsound(self.lastsound)

    if setsound != None:
      if self.lastbutton and self.lastsound :
        self.target.setbuttonsound(self.lastbutton, self.lastsound)
        self.updateused()

    #if have a target clock write data to it.
    self.target.controller = int(con)
    self.target.speed = float(speed)
    self.target.accel = float(accel)
    self.target.headturnlimit = float(headturnlimit)

    #If save button pressed then save settings to json file.
    if sv != None:
      self.target.save()

    self.do_GET()                               #Re-read the data.

  @classmethod
  def init( self, aTarget, aTesting ):
    '''  '''
    self.testing = aTesting
    if not self.testing:
      self.readHTML()

    self.target = aTarget
    self.getsoundfiles()                        #Make list of sound files.
#    print(self.soundFiles)
    self.updateused()

def run( aTarget, aTesting = False ):
  RH.init(aTarget, aTesting)

  server = HTTPServer(('', 8080), RH)
  server.timeout = 2.0 #handle_request times out after 2 seconds.
#  print("Starting server")

  #Loop as long as target clock is running or forever if we have none.
  while aTarget.running:
    server.handle_request()
    time.sleep(1.0)

  print('HTTP Server thread exit.')

if __name__ == '__main__':  #start server

  class testsnd(object):
    def __init__( self, aFile ):
      self.filename = aFile

  class testtarget(object):

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
      304 : testsnd('powerup'),
      305 : None,
      306 : None,
      307 : testsnd('hostiles'),
      308 : None,
      309 : None,
      310 : None,
      311 : None,
      312 : None,
      313 : None,
      314 : None,
      315 : None,
      316 : None,
      317 : None,
      318 : None,
      319 : None,
      320 : None
    }

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
      self.controller = 1
      self.speed = 50.0
      self.accel = 4.0
      self.headturnlimit = 90.0
      self._running = True
      self.startupsound = None

    def previewsound( self, aSound ):
      print("playing sound", aSound)

    def save( self ):
      print('Saving')

    def setbuttonsound( self, aButton, aFile ):
      print('Button sound:', aButton, aFile)

      if aFile:
        aFile = testsnd(aFile) if (aFile != 'None') else None

      if aButton == 'startup':
        self.startupsound = aFile
      else:
        btnnum = self.nametobtn(aButton)
        self.buttonsounds[btnnum] = aFile

    @property
    def running( self ): return self._running

  run(testtarget(), True)
  print('done')

