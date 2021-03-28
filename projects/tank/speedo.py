#!/usr/bin/env python3

import a3144

#--------------------------------------------------------
class speedo(object):
  """docstring for speedo"""

#--------------------------------------------------------
  def __init__(self, aPin):
    super(speedo, self).__init__()
    self._pin = aPin
    self._a = a3144.create(aPin)
    self._dist = 0
    self._time = 0
    self._dir = 1

#--------------------------------------------------------
  def __del__(self):
    a3144.release(self._a)

#--------------------------------------------------------
  @property
  def dir( self ):
    return self._dir

#--------------------------------------------------------
  @dir.setter
  def dir( self, aValue ):
    if aValue != 0:
      self._dir = 1 if aValue > 0 else -1

#--------------------------------------------------------
  @property
  def dist( self ):
    return self._dist

#--------------------------------------------------------
  @property
  def time( self ):
    return self._time

#--------------------------------------------------------
  def update( self, aDT ):
    ''' Update distance and time '''
    d, t = a3144.data(self._a)
    if d:
      self._dist += d * self._dir
      self._time += t

