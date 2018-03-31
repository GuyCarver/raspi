# Interactive Form for setting clock options.
#.

from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
from string import Template
import time
import cgi
import webbrowser
import woeid

#http://woeid.rosselliot.co.nz/lookup/21774

#todo: Handle time setting. C vs F?, revert from saved data?

HTML = Template('<html><head><style type="text/css">' +
  ' body {margin: 30px; font-family: sans-serif; background: #ddd;}' +
  ' span {font-style: italic; padding: 0 .5em 0 1em;}' +
  ' img {display: block; margin-left: auto; margin-right: auto; ' +
  'box-shadow: 5px 5px 10px 0 #666;}' +
  '</style></head><body>' +

  '<h2>Clock Settings</h2>' +
  '<form action="/" method="POST" enctype="multipart/form-data">' +
  '<label for="duration">Display Duration: </label>' +
  '<select name="duration" style="width:50px" onchange="form.submit()">' +
  '<option ${z_2}>2<option ${z_5}>5<option ${z_10}>10<option ${z_30}>30' +
  '</select> seconds<br/>' +
#  '<pre class="brush: css">#interval { width: 3em; }</pre>' +
  '<label for="interval">Object Check Interval: </label><input type="number" name="interval" ' +
  'step="0.1" min="0.1" max="1.0" list="intervallist" value="${interval}"></input> seconds' +
  '<datalist id="intervallist">' +
  '  <option value="0.1">' +
  '  <option value="0.25">' +
  '  <option value="0.5">' +
  '  <option value="0.75">' +
  '  <option value="1.0">' +
  '</datalist>' +
  '<h4>Temperature:' +
#  '<span>On </span>' +
  '<input type="checkbox" name="tempon" value="on" ' +
  'onclick="form.submit()" ${t_on}></h4>' + #<br/> ' +

  '<span>Zip Code:</span>' +
  '<input type="number" name="zipcode" value="${zipcode}"></input>' +
  '<input type="submit" name="gps" value="gps"><br/><br/><br/>' +

  '<datalist id="ticks"><option value="0" label="0"><option value="25">' +
  '<option value="50" label="50"><option value="75"><option value="100" label="100"></datalist> ' +
  '<span>Brightness:</span><input type="range" min="0" max="100" value="${bright}" name="bright" ' +
  'onchange="form.submit()" list="ticks">  ${bright}<br/>' +

  '<span>Temp Display Duration:</span>' +
  '<select name="tempduration" style="width:50px" onchange="form.submit()">' +
  '<option ${t_0}>0<option ${t_1}>1<option ${t_2}>2<option ${t_3}>3' +
  '<option ${t_4}>4<option ${t_5}>5</select> seconds<br/>' +

  '<span>Display Interval:</span>' +
  '<select name="display" style="width:50px" onchange="form.submit()">' +
  '<option ${i_10}>10<option ${i_15}>15<option ${i_30}>30</select> seconds<br/>' +

  '<span>Update Interval:</span>' +
  '<select name="update" style="width:50px" onchange="form.submit()">' +
  '<option ${u_5}>5<option ${u_10}>10<option ${u_15}>15' +
  '<option ${u_30}>30<option ${u_45}>45<option ${u_60}>60</select> minutes' +
  '<h3>Current Conditions:</h3>${conditions}' +

#  '<h3>Color:</h3>'
#  '<span><input type="color" name="color" value=${thecolor} '
#  'oninput="form.submit()"></span>' +

  '<h3>Sensor:</h3> ' +
  '<datalist id="ticks"><option value="0" label="0"><option value="2">' +
  '<option value="4" label="4"><option value="6"><option value="8" label="8"></datalist> ' +
  '<span>Variance:</span><input type="range" min="1" max="8" value="${variance}" name="variance" ' +
  'onchange="form.submit()" list="ticks">  ${variance}<br/><br/>' +
  '<span>On Time <input id="ontime" name="ontime" type="time" value=${ontime}></span>' +
  '<input type="submit" name="ontime" value="Set"><br/>' +
  '<span>Off Time <input id="offtime" name="offtime" type="time" value=${offtime}></span>' +
  '<input type="submit" name="offtime" value="Set"><br/><br/>' +
  '<input type="submit" name="Defaults" value="Defaults"><br/>'
  '<h3>Alarm</h3>' +
  '<span>Alarm: <input type="checkbox" name="alarmon" value="on" ' +
  'onclick="form.submit()" ${alarmon}><br/> ' +
  '<span><input id="alarm" name="alarm" type="time" value=${alarmtime}></span>' +
  '<input type="submit" name="SetAlarm" value="Set"><br/>' +
  '<br/><br/><input type="submit" name="Save" value="Save"><br/>' +
  '</form></body></html>')

class RH(BaseHTTPRequestHandler):

  ourTarget = None                                #Target Clock class.

  def determineloc(  ):
    '''Get a location from the Clock.'''
    return '21774' if RH.ourTarget == None else RH.ourTarget.location

  def determinedur(  ):
    '''Get a duration as z_??.'''
    dur = 5 if RH.ourTarget == None else int(RH.ourTarget.displayduration)
    return 'z_' + str(dur)

  def determinetempdur(  ):
    '''Get a duration as t_??.'''
    dur = 0 if RH.ourTarget == None else int(RH.ourTarget.tempdisplaytime)
    return 't_' + str(dur)

  def determinetempinterval(  ):
    '''Get a interval or i_10, 15 or 30.'''
    inter = 30 if RH.ourTarget == None else RH.ourTarget.tempdisplayinterval
    inters = ''
    if inter >= 30:
      inters = '30'
    elif inter >= 15:
      inters = '15'
    else:
      inters = '10'

    return 'i_' + inters

  def determineupdate(  ):
    '''Get update time of u_5, 10, 15, 30, 45 or 60.'''
    upd = 15.0 if RH.ourTarget == None else RH.ourTarget.tempupdateinterval
    upds = ''
    if upd >= 60.0:
      upds = '60'
    elif upd >= 45.0:
      upds = '45'
    elif upd >= 30.0:
      upds = '30'
    elif upd >= 15.0:
      upds = '15'
    elif upd >= 10.0:
      upds = '10'
    else:
      upds = '5'

    return 'u_' + upds

  def determineinterval(  ):
    return 0.1 if RH.ourTarget == None else RH.ourTarget.checkinterval

  def do_GET( self ):  #load initial page
#    print('getting ' + self.path)
    subs = {RH.determinedur() : 'selected', RH.determinetempdur() : 'selected',
      RH.determinetempinterval() : 'selected', RH.determineupdate() : 'selected',
      'zipcode': RH.determineloc(), 'interval' : RH.determineinterval() }

    #If we have a target read data from it.
    if RH.ourTarget != None:
      cond = RH.ourTarget.text + ' and ' + str(RH.ourTarget.temp) + ' degrees.'
      subs['conditions'] = cond

      if RH.ourTarget.tempdisplay:
        subs['t_on'] = 'checked'

      if RH.ourTarget.alarmenabled:
        subs['alarmon'] = 'checked'

      subs['alarmtime'] = RH.ourTarget.alarmhhmm

      subs['variance'] = str(RH.ourTarget.variance)

      br = str(int(RH.ourTarget.dim / 2.55))
      subs['bright'] = br

      aotimes = RH.ourTarget.alwaysontimeshhmm
      subs['ontime'] = aotimes[0]
      subs['offtime'] = aotimes[1]

      subs['thetime'] = RH.ourTarget.hhmm
      subs['thedate'] = RH.ourTarget.date
#      subs['thecolor'] = RH.ourTarget.colorstr

    self.send_response(200)
    self.send_header('Content-Type', 'text/html')
    self.end_headers()
    self.wfile.write(bytearray(HTML.safe_substitute(subs), 'utf-8'))

  def do_POST( self ):  #process requests
    #read form data
    form = cgi.FieldStorage(fp = self.rfile, headers = self.headers,
                            environ = {'REQUEST_METHOD':'POST',
                           'CONTENT_TYPE':self.headers['Content-Type']})
#    print(form)
    #Read data from forms into variables.
    dur = form.getfirst('duration')
    tdur = form.getfirst('tempduration')
    dis = form.getfirst('display')
    ud = form.getfirst('update')
    t = form.getfirst('tempon')
    g = form.getfirst('gps')
    zc = form.getfirst('zipcode')
    interval = form.getfirst('interval')
#    clr = form.getfirst('color')
    sv = form.getfirst('Save')
#    st = form.getfirst('SetTime')
    sa = form.getfirst('SetAlarm')
    variance = form.getfirst('variance')
    br = form.getfirst('bright')
    aenabled = form.getfirst('alarmon') != None
    atime = form.getfirst('alarm')
    ontime = form.getfirst('ontime')
    offtime = form.getfirst('offtime')
    defaults = form.getfirst('Defaults')

#    print('t = ' + str(t))
#    print('dur = ' + str(dur))
#    print('tempdur = ' + str(tdur))
#    print('dis = ' + str(dis))
#    print('ud = ' + str(ud))
#    print('vars {}, {}'.format(c, s))

    #If gps button pressed then get the zipcode from our IP address.
    if g != None:
#      print('doing gps')
      zc = woeid.zipfromip()

#    print(zc)

    #if have a target clock write data to it.
    if RH.ourTarget != None:
      RH.ourTarget.location = zc
      RH.ourTarget.checkinterval = float(interval)
      RH.ourTarget.tempdisplay = t == 'on'
      RH.ourTarget.displayduration = float(dur)
      RH.ourTarget.tempdisplaytime = int(tdur)
      RH.ourTarget.tempdisplayinterval = int(dis)
      RH.ourTarget.tempupdateinterval = float(ud) #Convert from minutes to seconds.
#      RH.ourTarget.colorstr = clr
      RH.ourTarget.variance = int(variance)
      RH.ourTarget.dim = (0xFF * int(br)) // 100
      if ontime != None and offtime != None:
        RH.ourTarget.alwaysontimeshhmm = (ontime, offtime)
#      RH.ourTarget.alarmenabled = aenabled
      if atime != None and sa != None:  #Only set alarm if the SetAlarm button pressed.
        RH.ourTarget.alarmhhmm = atime

      #If save button pressed then save settings to json file.
      if sv != None:
#        print('saving')
        RH.ourTarget.save()

      if defaults != None:
        RH.ourTarget.mlxdefaults()

    self.do_GET()                               #Re-read the data.

def run( aTarget ):
  RH.ourTarget = aTarget

  server = HTTPServer(('', 8080), RH)
  server.timeout = 2.0 #handle_request times out after 2 seconds.
#  print("Staring server")

  #Loop as long as target clock is running or forever if we have none.
  while RH.ourTarget == None or aTarget._running:
    server.handle_request()
    time.sleep(1.0)

  print('HTTP Server thread exit.')

if __name__ == '__main__':  #start server
  run(None)
  print('done')

