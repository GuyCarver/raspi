#!/usr/bin/env python3

#--------------------------------------------------------
class fuelgauge(object):
  ''' Watch battery level and report when it's below given voltage for given amount of time. '''

  #This value isn't consistent and seems to be slightly different based
  # on the battery.  So it's best to check the battery and adjust this value
  _VOLTS = 2616.72                              # (12.5v) Convert adc input to voltage

  #--------------------------------------------------------
  def __init__( self, aADC, aMin, aTime ):
    ''' aADC is an adcpin obect from the adc library. aMin is a minimum voltage
         to watch for. aTime is a time in seconds the voltage must be low
         before reporting bad. '''
    super(fuelgauge, self).__init__()

    self._adc = aADC
    self._min = aMin
    self._lowtime = 0.0
    self._time = aTime
    self.volts = 0.0

  #--------------------------------------------------------
  def update( self, aDT ):
    ''' Read voltage and report false if below minimum. '''

    self.volts = self._adc.value / fuelgauge._VOLTS
    good = self.volts >= self._min

    #if low only report bad after low for given time
    if not good:
      self._lowtime += aDT
      good = self._lowtime < self._time
    else:
      self._lowtime = 0.0                       # Reset the low time

    return good

#--------------------------------------------------------
if __name__ == '__main__':
  import adc
  from time import sleep
  a = adc.create(0x48)
  fp = adc.adcpin(a, 4)
  fgauge = fuelgauge(fp, 11.0, 10.0)
  print(fp.value)
  while 1:
    print(fgauge.update(0.1))
    sleep(0.1)
