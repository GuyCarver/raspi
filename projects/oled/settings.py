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

#todo: Handle time setting. C vs F?

HTML = Template('<html><head><style type="text/css">' +
  ' body {margin: 30px; font-family: sans-serif; background: #ddd;}' +
  ' span {font-style: italic; padding: 0 .5em 0 1em;}' +
  ' img {display: block; margin-left: auto; margin-right: auto; ' +
  'box-shadow: 5px 5px 10px 0 #666;}' +
  '</style></head><body>' +

  '<h2>Clock Settings</h2>' +
  '<form action="/" method="POST" enctype="multipart/form-data">' +
  '<span>Display Duration:</span>' +
  '<select name="duration" style="width:50px" onchange="form.submit()">' +
  '<option ${z_2}>2<option ${z_5}>5<option ${z_10}>10<option ${z_30}>30' +
  '</select> seconds<br/>' +

  '<h4>Temperature:' +
#  '<span>On </span>' +
  '<input type="checkbox" name="tempon" value="on" ' +
  'onclick="form.submit()" ${t_on}></h4>' + #<br/> ' +

  '<span>WOEID:</span>' +
  '<input type="text" name="woeid" value="${woeid}"></input>' +
  '<input type="submit" name="gps" value="gps"><br/>' +

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

  '<h3>Color:</h3>'
  '<span><input type="color" name="color" value=${thecolor} '
  'oninput="form.submit()"></span>' +

  '<h3>Date/Time:</h3>'
  '<span><input id="date" name="date" type="date" value=${thedate} ' +
  'oninput="form.submit()"></span>' +
  '<span><input id="time" name="time" type="time" value=${thetime} ' +
  'oninput="form.submit()"></span>' +
  '<br/><br/><input type="submit" name="Save" value="Save"><br/>' +
  '</form></body></html>')

class RH(BaseHTTPRequestHandler):

  ourTarget = None

  def determineloc(  ) :
    return '2483553' if RH.ourTarget == None else RH.ourTarget.location

  def determinedur(  ) :
    dur = 5 if RH.ourTarget == None else int(RH.ourTarget.displayduration)
    return 'z_' + str(dur)

  def determinetempdur(  ) :
    dur = 0 if RH.ourTarget == None else int(RH.ourTarget.tempdisplaytime)
    return 't_' + str(dur)

  def determineinterval(  ) :
    inter = 30 if RH.ourTarget == None else RH.ourTarget.tempdisplayinterval
    if inter >= 30:
      inter = 30
    elif inter >= 15:
      inter = 15
    else:
      inter = 10

    return 'i_' + str(inter)

  def determineupdate(  ) :
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

  def do_GET( self ) :  #load initial page
#    print('getting ' + self.path)
    subs = {RH.determinedur() : 'selected', RH.determinetempdur() : 'selected',
      RH.determineinterval(): 'selected', RH.determineupdate(): 'selected',
      'woeid': RH.determineloc() }

    if RH.ourTarget.tempdisplay :
      subs['t_on'] = 'checked'

    cond = ''
    if RH.ourTarget != None:
      cond = RH.ourTarget.text + ' and ' + str(RH.ourTarget.temp) + ' degrees.'

    subs['thetime'] = RH.ourTarget.hhmm
    subs['thedate'] = RH.ourTarget.date
    subs['thecolor'] = RH.ourTarget.colorstr
    subs['conditions'] = cond

    self.send_response(200)
    self.send_header('Content-Type', 'text/html')
    self.end_headers()
    self.wfile.write(bytearray(HTML.safe_substitute(subs), 'utf-8'))

  def do_POST( self ) :  #process requests
    #read form data
#    print('posting ' + self.path)
    form = cgi.FieldStorage(fp = self.rfile, headers = self.headers,
                            environ = {'REQUEST_METHOD':'POST',
                           'CONTENT_TYPE':self.headers['Content-Type']})
#    print(form)
    #assign variables
    dur = form.getfirst('duration')
    tdur = form.getfirst('tempduration')
    dis = form.getfirst('display')
    ud = form.getfirst('update')
    t = form.getfirst('tempon')
    g = form.getfirst('gps')
    w = form.getfirst('woeid')
    tm = form.getfirst('time')
    clr = form.getfirst('color')
    sv = form.getfirst('Save')

#    print('time = ' + str(tm))
#    print('t = ' + str(t))
#    print('dur = ' + str(dur))
#    print('tempdur = ' + str(tdur))
#    print('dis = ' + str(dis))
#    print('ud = ' + str(ud))
#    print('vars {}, {}'.format(c, s))

    if g != None :
#      print('doing gps')
      w = woeid.get()
#      print(w)

    if RH.ourTarget != None:
      RH.ourTarget.location = w
      RH.ourTarget.tempdisplay = t == 'on'
      RH.ourTarget.displayduration = float(dur)
      RH.ourTarget.tempdisplaytime = int(tdur)
      RH.ourTarget.tempdisplayinterval = int(dis)
      RH.ourTarget.tempupdateinterval = float(ud) #Convert from minutes to seconds.
      RH.ourTarget.colorstr = clr

      if sv != None :
#        print('saving')
        RH.ourTarget.save()

    self.do_GET()

def run( aTarget ) :
  RH.ourTarget = aTarget

  server = HTTPServer(('', 80), RH)
  server.timeout = 2.0 #handle_request times out after 2 seconds.
#  print("Staring server")

  if RH.ourTarget != None:
    while aTarget._running :
      server.handle_request()
      time.sleep(1.0)
#      print("handle_request")

#    print('Server thread Done')

if __name__ == '__main__':  #start server and open browser
  run(None)
  print('done')

