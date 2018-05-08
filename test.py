#my module test.

class myclass(object):
  '''docstring for myclass'''
  a, b, c, d, e, f = range(6)

  def __init__( self, arg ):
    super(myclass, self).__init__()
    self.arg = arg


def getname( aValue ):
  ''' '''
  for i in myclass.__dict__.items():
    if i[1] == aValue:
      return i[0]
  return None
