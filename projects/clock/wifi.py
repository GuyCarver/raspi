#read wifi signal strength.

import re

font = {"Width": 7, "Height": 8, "Start": 1, "End": 4, "Data": bytearray([
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, #wifi level 1.
  0x00, 0x00, 0x00, 0x00, 0xC0, 0x20, 0xA0, #wifi level 2.
  0x00, 0x00, 0xE0, 0x10, 0xC8, 0x28, 0xA8, #wifi level 3.
  0xF0, 0x08, 0xE4, 0x12, 0xCA, 0x2A, 0xAA, #wifi level 4.
])}

check = re.compile('.*wlan0: .* *[0-9]*\\.. *(.*)\\.')

def signal(  ):
  '''Read wireless signal from /proc/net/wireless file. Range is 0 to -100 with 0 being strongest.'''
  sig = -100
  try:
    with open('/proc/net/wireless', 'r') as f:
      f.readline() #Skip the header lines.
      f.readline()
      h = f.readline() #Read the data then parse the level value.
      g = check.match(h)
      if g != None:
        sig = int(g.group(1))
  except Exception as e:
    print(e)

  return(sig)

def signal2level( aSignal ):
  '''aSignal between 0 and -100.
     Return level value 0-4
     4 = <= -54
     3 = <= -61
     2 = <= -68
     1 = <= -75
     0 = > -75 (No useable signal)'''
  return min(max(0, (82 + aSignal) // 7), 4)

def level(  ):
  '''Read wireless signal strength, then convert to level 0-4.'''
  return signal2level(signal())

#from time import sleep

#def main(  ):
#  while True:
#    v = signal()
#    print(v)
#    sleep(2.0)
