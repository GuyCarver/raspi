from time import sleep

class testinterp(object):
  '''docstring for testinter'''
  def __init__( self ):
    self._speed = 0.0
    self._targetspeed = 100.0
    self._rate = 100.0

  def update( self, aDelta ):
    '''Update speed towards target given delta time in seconds.'''
    diff = self._targetspeed - self._speed

    if diff != 0.0:
      #If no rate or diff too small just set directly.

      if (self._rate > 0.0) and (abs(diff) > 0.01):
        #Interpolate between src, target by delta.
        if diff < 0:
          mm = max
          aDelta *= -1.0
        else:
          mm = min

        diff = mm(self._rate * aDelta, diff)
        newspeed = self._speed + diff
        self._speed = mm(newspeed, self._targetspeed)
      else:
        self._speed = self._targetspeed

if __name__ == '__main__':  #start server
  t = testinterp()
  def waitforit():
    while t._speed != t._targetspeed:
      t.update(0.01)
      print(t._speed)
      sleep(0.01)

  t._targetspeed = 100.0
  waitforit()
  t._targetspeed = 0.0
  waitforit()
