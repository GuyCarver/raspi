#!/usr/bin/env python3

#--------------------------------------------------------
class fuelgauge(object):
  ''' Watch battery level and report. '''

  #This value isn't consistent and seems to be slightly different based
  # on the battery.  So it's best to check the battery and adjust this value
  _VOLTS = 3216.0                               # Convert adc input to voltage

  #--------------------------------------------------------
  def __init__( self, aADC, aMin ):
    ''' aADC is an adcpin obect from the adc library. aMin is a minimum voltage
         to watch for. '''
    super(fuelgauge, self).__init__()

    self._adc = aADC
    self._min = aMin
    self.volts = 0.0

  #--------------------------------------------------------
  def update( self ):
    ''' Read voltage and report false if below minimum. '''

    self.volts = self._adc.value / fuelgauge._VOLTS
    return self.volts < self._min
