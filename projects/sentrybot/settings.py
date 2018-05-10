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

#'<html><head><style type="text/css">'
#  ' body {margin: 30px; font-family: sans-serif; background: #ddd;}'
#  ' span {font-style: italic; padding: 0 .5em 0 1em;}'
#  ' img {display: block; margin-left: auto; margin-right: auto; '
#  'box-shadow: 5px 5px 10px 0 #666;}'

HTML = Template('<html><head>'
  '<meta name="viewport" content="width=device-width, initial-scale=1">'
  '<title>SentryBot</title>'
  '<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css">'
  '<style>'
  '.slidecontainer {'
  '    width: 200px;'
  '}'
  '</style></head><body>'
  '<form action="/" method="POST" enctype="multipart/form-data">' +
  '<div class="container">'
  '<div><h1>Sentrybot Settings</h1><div>'
  '<div>'
  '  <h2>Controller</h2>'
  '  <div><input type="radio" name="controller" value="0" ${c_0} onclick="form.submit()">8Bitdo FC30 Pro</div>'
  '  <div><input type="radio" name="controller" value="1" ${c_1} onclick="form.submit()">PS2</div>'
  '<div></br></br>'
  '<div class="slidecontainer">'
  '<datalist id="ticks"><option value="0" label="0"><option value="25">'
  '<option value="50" label="50"><option value="75"><option value="100" label="100"></datalist> '
  '<span>Speed: ${speed}</span><input type="range" min="0" max="100" value="${speed}" name="speed" '
  'onchange="form.submit()" list="ticks">'
  '</div></br>'
  '<div class="slidecontainer">'
  '<span>Accel: ${accel}</span><input type="range" min="0" max="100" value="${accel}" name="accel" '
  'onchange="form.submit()" list="ticks">'
  '</div></br>'
  '<div>'
  '<label for="startup">Startup Sound:  </label>'
  '<select name="startup" style="width:150px" onchange="form.submit()">'
  '${startup}</select><br/>'
  '</div></br>'
  '<div>${buttons}</div>'
  '<div>'
  '<input type="submit" name="Save" value="Save">'
  '</div></div>'
  '</form></body></html>')

#  '<datalist id="sounds">'
#  '${startup}'
#  '</datalist>'
#  '<div><label for="A">A: </label><input list="sounds" name="A"></div>'
#  '<div><label for="B">B: </label><input list="sounds" name="B"></div>'
#  '<div><label for="C">C: </label><input list="sounds" name="C"></div>'
#  '<div><label for="D">D: </label><input list="sounds" name="D"></div>'

class RH(BaseHTTPRequestHandler):

  target = None                                #Target Clock class.
  sounddir = 'sounds'
  soundFiles = []                               #List of sound files in sounds directory.
  buttonlist = []                               #List of button names.

  def determinecontroller(  ):
    return 'c_' + str(RH.target.controller)

  @classmethod
  def getsoundfiles( self ):
    self.soundFiles = [splitext(f)[0] for f in listdir(self.sounddir) if isfile(join(self.sounddir, f))]
    self.soundFiles.sort()
    self.soundFiles.insert(0, 'None')

  @classmethod
  def makesoundlist( self, selection ):
    def makeit(f):
      tag = ' selected' if selection == f else ''
      return '<option{}>{}</option>'.format(tag, f)

    return ''.join([makeit(f) for f in self.soundFiles])

  @classmethod
  def buildbuttonlist( self, buttons ):
    '''  '''
    self.buttonlist = [self.target.btntoname(n) for n in buttons.keys()]

  @classmethod
  def buildbuttonsounds( self, buttons ):
    res = ''
#    print(buttons)
#    print(self.buttonlist)
    for i, s in enumerate(buttons.values()):
      bname = self.buttonlist[i]
      fname = s.filename if s else 'None'
      slist = self.makesoundlist(fname)
      res += '''<div><label for="{0}">{0}:</label>
                <select name="{0}" style="width:150px" onchange="form.submit()">
                {1}</select></div>'''.format(bname, slist)
    return res

  def do_GET( self ):  #load initial page
#    print('getting ' + self.path)
    subs = { RH.determinecontroller() : 'checked',
      'speed' : RH.target.speed,
      'accel' : RH.target.accel,
      'startup' : RH.makesoundlist(RH.target.startupsound),
     'buttons' : RH.buildbuttonsounds(RH.target.buttonsounds)
    }

    self.send_response(200)
    self.send_header('Content-Type', 'text/html')
    self.end_headers()
    inter = HTML.safe_substitute(subs)
#    print(inter)
    self.wfile.write(bytearray(inter, 'utf-8'))

  def do_POST( self ):  #process requests
    #read form data
    form = cgi.FieldStorage(fp = self.rfile, headers = self.headers,
                            environ = {'REQUEST_METHOD':'POST',
                           'CONTENT_TYPE':self.headers['Content-Type']})
#    print(form)
    #Read data from forms into variables.
    con = form.getfirst('controller')
    startup = form.getfirst('startup')
    speed = form.getfirst('speed')
    accel = form.getfirst('accel')
    sv = form.getfirst('Save')

    #todo: Loop through button sounds and parse.
    for btn in self.buttonlist:
      soundname = form.getvalue(btn)
      RH.target.setbuttonsound(btn, soundname)

    #if have a target clock write data to it.
    RH.target.controller = int(con)
    RH.target.speed = float(speed)
    RH.target.accel = float(accel)
    RH.target.startupsound = startup

    #If save button pressed then save settings to json file.
    if sv != None:
#       print('saving')
      RH.target.save()

    print('controller = ', RH.target.controller)
    print('speed = ', RH.target.speed)
    print('accel = ', RH.target.accel)
    print('startup = ', RH.target.startupsound)

    self.do_GET()                               #Re-read the data.

def run( aTarget ):
  RH.target = aTarget
  RH.buildbuttonlist(aTarget.buttonsounds)      #Build list of button names.
  RH.getsoundfiles()                            #Make list of sound files.
#  print(RH.soundFiles)

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

    '''docstring for testtarget'''
    def __init__( self ):
      self.controller = 1
      self.speed = 50.0
      self.accel = 4.0
      self._running = True
      self.startupsound = 'powerup'

    def save( self ):
      print('saving')

    def setbuttonsound( self, aButton, aFile ):
      '''  '''
      print("Sound:", aButton, aFile)
      btnnum = self.nametobtn(aButton)
      if aFile:
        aFile = testsnd(aFile)
      self.buttonsounds[btnnum] = aFile

    @property
    def running( self ): return self._running

  run(testtarget())
  print('done')

