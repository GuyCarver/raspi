#!/usr/bin/env python3

#todo: Create functions to work with state start/update/end.
#States are going to be a dictionary.

_START, _UPDATE, _INPUT, _END = range(4)

#Function signatures
#start(self, *aArgs)
#update(self, DeltaTime)
#end(self, *aArgs)

#--------------------------------------------------------
def create( *, s = None, u = None, i = None, e = None ):
  ''' '''
  return { _START: s, _UPDATE: u, _INPUT: i, _END: e }

#--------------------------------------------------------
def run( aState, aKey, aArgs ):
  ''' '''
  fn = aState.get(aKey)
  if fn != None:
    fn(aState, *aArgs)

#--------------------------------------------------------
def update( aState, *aArgs ):
  ''' '''
  run(aState, _UPDATE, aArgs)

#--------------------------------------------------------
def start( aState, *aArgs ):
  ''' '''
  run(aState, _START, aArgs)

#--------------------------------------------------------
def input( aState, *aArgs ):
  ''' '''
  run(aState, _INPUT, aArgs)

#--------------------------------------------------------
def end( aState, *aArgs ):
  ''' '''
  run(aState, _END, aArgs)

