#!/usr/bin/env python3
#----------------------------------------------------------------------
# Copyright (c) 2021, gcarver
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above copyright notice,
#       this list of conditions and the following disclaimer in the documentation
#       and/or other materials provided with the distribution.
#
#     * The name of Guy Carver may not be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# FILE    state.py
# BY      gcarver
# DATE    04/13/2021 01:44 PM
#----------------------------------------------------------------------

_START, _UPDATE, _INPUT, _END = range(4)

#--------------------------------------------------------
def create( *, s = None, u = None, i = None, e = None ):
  ''' Create a state object '''
  return { _START: s, _UPDATE: u, _INPUT: i, _END: e }

#--------------------------------------------------------
def run( aState, aKey, aArgs ):
  ''' Run the given state process indicated by aKey. '''
  fn = aState.get(aKey)
  if fn != None:
    fn(aState, *aArgs)

#--------------------------------------------------------
def update( aState, *aArgs ):
  ''' Run the update state. '''
  run(aState, _UPDATE, aArgs)

#--------------------------------------------------------
def start( aState, *aArgs ):
  ''' Run the start state. '''
  run(aState, _START, aArgs)

#--------------------------------------------------------
def input( aState, *aArgs ):
  ''' Run the input state. '''
  run(aState, _INPUT, aArgs)

#--------------------------------------------------------
def end( aState, *aArgs ):
  ''' Run the end state. '''
  run(aState, _END, aArgs)

