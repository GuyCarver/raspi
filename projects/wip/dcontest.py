
import functools
import pyudev
from time import sleep

context = pyudev.Context()
monitor = pyudev.Monitor.from_netlink(context)
monitor.filter_by('input')

def log_event(action, device):
  if device.sys_name == 'js0':
    print(action, device.sys_name)
    print(device.device_node)
    print(device.device_number)
    print(device.device_type)

observer = pyudev.MonitorObserver(monitor, log_event)
observer.start()

while 1:
  sleep(1.0)