
import pygame
from sound import *
from time import sleep

pygame.init()
pygame.display.init()

s = soundchain(('sys/powerup', 'sys/one'), 1)
s.play()

while(1):
  e = pygame.event.get()
  if e != None:
    print(e)
  sleep(0.1)
