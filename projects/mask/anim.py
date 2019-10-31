#!/usr/bin/env python3

#note: PINPONG doesn't work.  Need to make a _realkey value and keep it up to date
# for both LOOP and PINGPONG.  The algorythm for PINGPONG isn't correct.

#------------------------------------------------------------------------
class anim(object):
  '''docstring for anim
  key = (value, rate)
  _DIRECT - 1 key, set's directly with no animation.
  _ONCE - Multiple keys, plays until all keys used.
  _PINPONG - Multiple keys, plays to end then goes backwards forever.
  _LOOP - Multiple keys, plays to end then starts over.
  '''

  _DIRECT, _ONCE, _PINGPONG, _LOOP = range(4)

#------------------------------------------------------------------------
  def __init__( self, aKeys, aType ):
    super(anim, self).__init__()
    self._keys = aKeys
    self._key = 0
    self._value = 0
    self._dir = 0
    self._target = 0
    self._type = aType

    #If not a sequence of values then it's always direct.
    if isinstance(aKeys, (int, float)):
      self._type = anim._DIRECT
    else:
      if len(aKeys) <= 1:
        raise('Need at least 2 keys')
      self._dir = 1

    self._start()

  @property
  def type( self ):
    return self._type

  @type.setter
  def type( self, aType ):
    self._type = aType

  @property
  def done( self ):
    return self._dir == 0

  @property
  def key( self ):
    return self._key

  @property
  def value( self ):
    return self._value

  @value.setter
  def value( self, aValue ):
    #Can only set value if direct.
    if self._type == anim._DIRECT:
      self._value = aValue

  def _start( self ):
    if self._type > anim._DIRECT:
      v, r = self._keys[self._key]
      self._target = v
      self._nextkey()
    else:
      self._value = self._keys

  def restart( self ):
    '''  '''
    self._key = 0
    self._dir = 1
    self._start()

  def _getindex( self ):
    '''  '''
    ln = len(self._keys)

    #Loop
    k = self._key % ln
    animdir = 1

    #pingpong
    if self._type == anim._PINGPONG:
      animdir = 1 - (((self._key // ln - 1) & 1) << 1)
      print('ad', animdir)

    if animdir < 0:
      k = (ln - 1) - k

    return k

  def _nextkey( self ):
    '''  '''
    self._key += 1
    self._value = self._target

#0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12
#0, 1, 2, 3, 2, 1, 0, 1, 2, 3, 2,  1,  0

    #Once
    if self._type == anim._ONCE:
      if self._key >= len(self._keys):
        self._dir = 0 #done.
        return

    k = self._getindex()

    self._target, rate = self._keys[k]
    self._dir = self._target - self._value
    if rate > 0:
      self._dir /= rate

  def update( self, aDT ):
    '''  '''
    if self._dir:
      self._value += self._dir * aDT
      if self._dir < 0:
        if self._value <= (self._target + 0.001):
          self._nextkey()
      else:
        if self._value >= (self._target - 0.001):
          self._nextkey()

#def test2():
#  ln = 4
#  for i in range(13):
#    animdir = 1 - (((i // ln - 1) & 1) << 1)
#    k = i % ln
#    if animdir > 0:
#      k = (ln - 1) - k
#    print(i, animdir, k)
#
def test():
  keys = ((0.1, 1.0), (50.0, 1.0), (0.0, 1.0))
  o = anim(keys, anim._ONCE)
  l = anim(keys, anim._LOOP)

  for i in range(320):
    o.update(0.1)
    l.update(0.1)

    print('o', o.value)
    print('l', l.value)

  print('done.')

if __name__ == '__main__':
#test.
  test()

