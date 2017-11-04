
from oled import *
import time

#pip install weather-api
# Check this out for how to possibly read the data without weather-api
#https://developer.yahoo.com/weather/documentation.html
from weather import Weather
weather = Weather()

#  0
#1   2
#  3
#4   5
#  6
segs = [(0,0,0), (0,0,1), (1,0,1), (0,1,0), (0,1,1), (1,1,1), (0,2,0),
        (1,0,0), (2,0,1), (1,1,0), (2,1,1), (2,2,0)]
adj = 2
nums = [[0,1,2,4,5,6], [2,5], [0,2,3,4,6], [0,2,3,5,6], [1,2,3,5],
        [0,1,3,5,6], [0,1,3,4,5,6], [0,2,5], [0,1,2,3,4,5,6], [0,1,2,3,5]]

apm = [(0,1,2,3,4,5), (0,1,2,3,4), (0,1,2,4,5,7,8,10), (0,1,2,3)]

digitpos = [0.0, 1.3, 3.1, 4.4, 6.0]
twoline = 7
threeline = 10
tempinterval = 30
tempdur = 3
tempsize = 6

class MyScene:
  def __init__(self):
    #Frederick = 2458710
    #Rockville = 2483553
    self.location = 2458710
    self.wh = 15
    self.x = 5.0
    self.y = 10.0
    self.size = (128, 64)
    self.i2c = oled()
    self.digits = (0, 0, 0, 0, 0, 0)
    self.temp = 0
    self.tempset = False

  def iline(self, sx, sy, ex, ey):
    self.i2c.line((int(sx), int(sy)), (int(ex), int(ey)), 1)

  def drawseg(self, pos, seg, wh):
    x,y,d = seg
    x = x * wh + pos[0]
    y = y * wh + pos[1]
    if d == 0:
      sx = x + adj
      ex = sx + wh - adj
      self.iline(sx, y+1, ex, y+1)
      sx += 1
      ex -= 1
      if wh >= twoline:
        self.iline(sx,y,ex,y)
      if wh >= threeline :
        self.iline(sx,y+2,ex,y+2)
    else:
      sy = y + 1
      ey = sy + wh - 1
      self.iline(x+1, sy, x+1, ey)
      sy += 1
      ey -= 1
      if wh >= twoline:
        self.iline(x,sy,x,ey)
      if wh >= threeline :
        self.iline(x+2,sy,x+2,ey)

  def drawsegs(self, pos, seglist, wh):
    for s in seglist:
      self.drawseg(pos, segs[s], wh)

  def draw(self):
    self.i2c.clear()
    x = int(self.x)
    y = int(self.y)

    def drawdig(anum):
      p =  (x + (self.wh * digitpos[anum]), y)
      self.drawsegs(p, nums[self.digits[anum]], self.wh )

    def drawapm(anum):
      wh = self.wh // 2
      p = (x + (self.wh * digitpos[anum]), y)
      d = self.digits[anum]
      self.drawsegs(p, apm[d], wh)
      if d < 2:
        p = (p[0] + wh + (wh // 2) + 1, y)
        self.drawsegs(p, apm[2], wh)

    drawdig(0)
    drawdig(1)
    drawdig(2)
    drawdig(3)
    drawapm(4)

    p = (x + (self.wh * digitpos[4]), y + 3 + (self.wh * 2))
    wh = tempsize
    n1 = (self.temp // 10) % 10
    n2 = self.temp % 10
    self.drawsegs(p, nums[n1], wh)
    p = (p[0] + wh + 2, p[1])
    self.drawsegs(p, nums[n2], wh)
    p = (p[0] + wh + 4, p[1])
    self.drawsegs(p, apm[3], wh)

    def drawrect(pos):
      self.i2c.fillrect(pos, (3,3), 1)

    if (self.digits[5] & 1) == 1:
      sx = (digitpos[1] + 1.0 + digitpos[2]) / 2
      sy = (self.wh // 3) * 2
      p = (int((sx * self.wh) + self.x), int(self.y + sy))
      drawrect(p)
      sy += sy
      p = (p[0], int(self.y + sy))
      drawrect(p)

    self.i2c.display()

  def UpdateTime(self):
    t = time.localtime()
    h = t.tm_hour
    m = t.tm_min
    s = t.tm_sec
    apm = 0
    if h >= 12:
      apm = 1
      if h > 12:
        h -= 12

    if (s % tempinterval) < tempdur:
      h = 0
      if not self.tempset:
        try:
          lookup = weather.lookup(self.location)
          condition = lookup.condition()
          self.temp = int(condition['temp'])
        except Exception as e:
          pass
        self.tempset = True
      m = self.temp
      apm = 3
    else:
      self.tempset = False

    self.digits = (h // 10, h % 10, m // 10, m % 10, apm, s)

  def run(self):
    runit = True
    while runit:
      self.UpdateTime()
      self.draw()
      time.sleep(0.2)

def run():
  scn = MyScene()
  scn.run()

if __name__ == '__main__':
  run()
