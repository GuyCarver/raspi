import json
import console

fname = 'clock.json'

def savedefaults(  ):
  try:      
    with open(fname, 'w+') as f:
      data = {}
      data['on'] = True
      data['duration'] = 3
      data['interval'] = 30
      data['update'] = 30
      data['location'] = 12345
      
      json.dump(data, f)
  except:
    pass


def loaddefaults(  ):
  try:
    with open(fname, 'r') as f:
      data = json.load(f)
      print(data)
  except:
    pass

console.clear()
savedefaults()
loaddefaults()

