#!/usr/bin/env python3

#LynxMotion PS2 wireless controller driver.
#See http://www.lynxmotion.com/images/files/ps2cmd01.txt for command list.
#See http://sophiateam.undrgnd.free.fr/psx/index.html for explanation of communication protocol.

import wiringpi

#todo: Need to error check and attempt reconnect when failing to read data.

class ps2():
  '''PS2 wireless controller driver. Each button tracks up/down state as well
     as just pressed/released state.  These values may be read directly or
     state changes may be reported to a given callback function.  The L/R Joystick
     values are in the range of +/- 256 and must be read using the joy() function.
     The PS2 controller is put into analog mode without pressure sensitivity on the buttons.
     Rumble is not enabled.  Enabling rumble for some reason causes input to be extremely slow.'''

  #Button values. Bit 1 = changed, Bit 0 = Down state.
  _UP         = 0
  _DOWN       = 1 #Button is down.
  _RELEASED   = 2 #Indicates button was just released.
  _PRESSED    = 3 #Indicate button was just pressed.

  #_buttons array indexes
  _SELECT     = 0
  _L_HAT      = 1
  _R_HAT      = 2
  _START      = 3
  _DPAD_U      = 4
  _DPAD_R      = 5
  _DPAD_D      = 6
  _DPAD_L      = 7
  _L_TRIGGER  = 8
  _R_TRIGGER  = 9
  _L_SHOULDER = 10
  _R_SHOULDER = 11
  _TRIANGLE   = 12
  _CIRCLE     = 13
  _CROSS      = 14
  _SQUARE     = 15

  #_joys array indexes.
  _RX = 0
  _RY = 1
  _LX = 2
  _LY = 3

  #Controller commands.
  _qmode = (1,0x41,0,0,0)       #Add the below bytes in to read analog (analog button mode needs to be set)
  _qdata = (1,0x42,0,0,0,0,0,0,0) #,0,0,0,0,0,0,0,0,0,0,0,0,0) #If we wanted rumble, bytes 3 and 4 would need to be set.
  _enter_config = (1,0x43,0,1,0)
  _exit_config = (1,0x43,0,0,0x5A,0x5A,0x5A,0x5A,0x5A)
  _set_mode = (1,0x44,0,1,3,0,0,0,0) #1 = analog stick mode, 3 = lock mode button.
#  _ds2_native = (1,0x4F,0,0xFF,0xFF,03,00,00,00)
#  _enable_analog = (1,0x4F,0,0xFF,0xFF,3,0,0,0) #enable analog pressure input from buttons.
#  _enable_rumble = (0x01,0x4D,0,0,1)
#  _type_read= (1,0x45,0,0,0,0,0,0,0)

  def __init__( self, aCmd, aData, aClk, aAtt, aCallback = None ):
    '''Create a ps2 object with the given Command, Data, Clock, Attn and Callback values.'''
    wiringpi.wiringPiSetupGpio()

    self._cmd = aCmd
    wiringpi.pinMode(aCmd, 1)
    self._data = aData
    wiringpi.pinMode(aData, 0)
    self._clk = aClk
    wiringpi.pinMode(aClk, 1)
    self._att = aAtt
    wiringpi.pinMode(aAtt, 1)
    self._res = bytearray(9)  #Set this to 22 for analog button data reading.
    #Double buffered button data.
    self._buttons = (bytearray(16), bytearray(16))
    self._buttonIndex = 0                       #Index into _buttons array.
    self._joys = [0, 0, 0, 0]
    #If we don't set these high to start the 1st command doesn't work.
    wiringpi.digitalWrite(self._att, 1)
    wiringpi.digitalWrite(self._clk, 1)
    self._callback = None
    self._initpad()
    #Set callback after _initpad() because button states change during init.
    self.callback = aCallback

  def _sendrcv( self, aSend ):
    '''Send data in aSend while reading data into _res'''
    #Try these to see if they help.
    wiringpi.digitalWrite(self._cmd, 1)
    wiringpi.digitalWrite(self._clk, 1)

    wiringpi.digitalWrite(self._att, 0)

    wiringpi.delayMicroseconds(2)               #Wait a bit before sending.

    #Send each byte and receive a byte.
    for i, b in enumerate(aSend):
      value = 0
      #Shift bits from b onto _cmd pin while reading bits into value from _data pin.
      for j in range(0, 8):
        wiringpi.digitalWrite(self._cmd, b & 1)  #Set/Clear pin for bit of aChar.
        b >>= 1               #Next bt.
        wiringpi.digitalWrite(self._clk, 0)
        wiringpi.delayMicroseconds(3)
        value |= wiringpi.digitalRead(self._data) << j  #Read bit from data pin.
        wiringpi.digitalWrite(self._clk, 1)     #Set clock high.
      self._res[i] = value
      wiringpi.delayMicroseconds(3)

    wiringpi.digitalWrite(self._att, 1)         #Tell controller we are done sending data.
    return self._res

  def _reconnect( self ):
    '''Resend config data to controller.'''
    self._sendrcv(ps2._enter_config)
    wiringpi.delayMicroseconds(3)
    self._sendrcv(ps2._set_mode)
    #Put these in to enable rumble and analog button modes.
    # I took out because they cause a delay in button/stick input for some reason.
#    self.display()
#    self._sendrcv(ps2._enable_rumble)
#    self.display()
#    self._sendrcv(ps2._enable_analog)
#    self.display()
    wiringpi.delayMicroseconds(3)
    self._sendrcv(ps2._exit_config)

  def _initpad( self ):
    '''Initialize the gamepad in analog stick mode.'''
    self.qdata()             #Without a read/delay, config fails.
    wiringpi.delayMicroseconds(100)
    self._reconnect()
    #Read data a few times to get junk out of the way.
    for i in range(0, 6):
      wiringpi.delayMicroseconds(3)
      self.qdata()

#  def qmode( self ):
#    '''  '''
#    return self._sendrcv(ps2._qmode)

  @property
  def callback( self ):
    return self._callback

  @callback.setter
  def callback( self, aCallback ):
    self._callback = aCallback

  @property
  def curbuttons( self ):
    return self._buttons[self._buttonIndex]

  @property
  def prevbuttons( self ):
    return self._buttons[not self._buttonIndex]

  def button( self, aIndex ):
    return self.curbuttons[aIndex]

  def joy( self, aIndex ):
    return self._joys[aIndex]

  def qdata( self ):
    '''Read button/joystick data from controller.  Data will be in _res.'''
    self._sendrcv(ps2._qdata)

    #Swap buffer for current button values.
    self._buttonIndex = not self._buttonIndex
    #Get previous and current button buffers.
    prev = self.prevbuttons
    buttons = self.curbuttons
    btns = self._res[3] | (self._res[4] << 8) #Merge 16 bits of button data.
    for i in range(16):
      bv = not (btns & 1)       #Button on if bit is 0 in btns, so swap bit value.
      if bv != (prev[i] & 1):   #If button changed, set bit 1.
        bv |= 2
      buttons[i] = bv

      #If value not _UP and we have a callback function, then call it.
      if bv and self._callback:
        self._callback(i, bv)

      btns >>= 1                #Next button bit.

    #Convert joystick values 0-0xFF with 0x80 in center to values +/- 0-256
    sgn = 1
    for i in range(5, 9):
      self._joys[i - 5] = ((self._res[i] - 0x80) << 1) * sgn
      sgn = -sgn  #Every other value (y) needs to be reversed so +y is up.

    return self._res

#  def displaymode( self ):
#    self.display(self.qmode())

#  def displaydata( self ):
#    self.display(self.qdata())

#  def displaymodel( self ):
#    self.display(self._sendrcv(ps2._type_read))

  def display( self, aBuf = None ):
    if aBuf == None :
      aBuf = self._res

    for b in aBuf:
      print(hex(b), end='')
      print(',', end='')
    print(';', end='\r')

  def test( self ):
    while 1:
      v = self.qdata()
      self.display(v)
#      print(self.curbuttons, end=' ')
#      print(self._joys, end='\r')
      wiringpi.delayMicroseconds(7000)

#btnnames = ['SELECT', 'L_HAT', 'R_HAT', 'START', 'DPAD_U', 'DPAD_R',
#      'DPAD_D', 'DPAD_L', 'L_TRIGGER', 'R_TRIGGER', 'L_SHOULDER',
#      'R_SHOULDER', 'TRIANGLE', 'CIRCLE', 'CROSS', 'SQUARE']
#
#statenames = ['UP', 'DOWN', 'RELEASED', 'PRESSED']
#
#def MyCallback( aIndex, aState ):
#  ''' '''
#  print('{} : {}'.format(btnnames[aIndex], statenames[aState]))
#
#clk = 18, att = 17, cmd = 27, dat = 22
def test(  ):
  p = ps2(27, 22, 18, 17, None)
  p.test()
#  while 1:
#    p.qdata()
#    sleep_us(50000)
