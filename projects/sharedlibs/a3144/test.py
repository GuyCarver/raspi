#!/usr/bin/env python3

import a3144
from time import sleep

gpioinit()
h = a3144.create(22)

while True:
  c, t = a3144.data(h)
  if c:
    print(c, t)
  sleep(1.0)
