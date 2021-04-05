
'''
        Read Gyro and Accelerometer by Interfacing Raspberry Pi with MPU6050 using Python
	http://www.electronicwings.com
'''
import smbus			#import SMBus module of I2C
from time import sleep          #import

#some MPU6050 Registers and their Address
PWR_MGMT_1   = 0x6B
SMPLRT_DIV   = 0x19
CONFIG       = 0x1A
GYRO_CONFIG  = 0x1B
INT_ENABLE   = 0x38
ACCEL_XOUT_H = 0x3B
ACCEL_YOUT_H = 0x3D
ACCEL_ZOUT_H = 0x3F
GYRO_XOUT_H  = 0x43
GYRO_YOUT_H  = 0x45
GYRO_ZOUT_H  = 0x47

AxCal, AyCal, AzCal = (0.0, 0.0, 0.0)
GxCal, GyCal, GzCal = (0.0, 0.0, 0.0)

def MPU_Init():
	#write to sample rate register
	bus.write_byte_data(Device_Address, SMPLRT_DIV, 7)
	
	#Write to power management register
	bus.write_byte_data(Device_Address, PWR_MGMT_1, 1)
	
	#Write to Configuration register
	bus.write_byte_data(Device_Address, CONFIG, 0)
	
	#Write to Gyro configuration register
	bus.write_byte_data(Device_Address, GYRO_CONFIG, 24)
	
	#Write to interrupt enable register
	bus.write_byte_data(Device_Address, INT_ENABLE, 1)

def read_raw_data(addr):
	#Accelero and Gyro value are 16-bit
  try:
    high = bus.read_byte_data(Device_Address, addr)
    low = bus.read_byte_data(Device_Address, addr+1)

    #concatenate higher and lower value
    value = ((high << 8) | low)

    #to get signed value from mpu6050
    if(value > 32768):
      value -= 65536
  except:
    value = 0

  return value

def Callibrate(  ):
  global AxCal
  global AyCal
  global AzCal
  global GxCal
  global GyCal
  global GzCal

  samples = 50

  x = 0
  y = 0
  z = 0

  for i in range(samples):
    x += read_raw_data(ACCEL_XOUT_H)
    y += read_raw_data(ACCEL_YOUT_H)
    z += read_raw_data(ACCEL_ZOUT_H)

  As = samples * 16384.0

  AxCal = x / As
  AyCal = y / As
  AzCal = z / As

  x = 0
  y = 0
  z = 0

  for i in range(samples):
    x += read_raw_data(GYRO_XOUT_H)
    y += read_raw_data(GYRO_YOUT_H)
    z += read_raw_data(GYRO_ZOUT_H)

  As = samples * 131.0

  GxCal = x / As
  GyCal = y / As
  GzCal = z / As

bus = smbus.SMBus(1) 	# or bus = smbus.SMBus(0) for older version boards
Device_Address = 0x68   # MPU6050 device address

MPU_Init()
Callibrate()

print (" Reading Data of Gyroscope and Accelerometer")

while True:
	
	#Read Accelerometer raw value
	acc_x = read_raw_data(ACCEL_XOUT_H)
	acc_y = read_raw_data(ACCEL_YOUT_H)
	acc_z = read_raw_data(ACCEL_ZOUT_H)
	
	#Read Gyroscope raw value
	gyro_x = read_raw_data(GYRO_XOUT_H)
	gyro_y = read_raw_data(GYRO_YOUT_H)
	gyro_z = read_raw_data(GYRO_ZOUT_H)
	
	#Full scale range +/- 250 degree/C as per sensitivity scale factor
	Ax = (acc_x / 16384.0) - AxCal
	Ay = (acc_y / 16384.0) - AyCal
	Az = (acc_z / 16384.0) - AzCal
	
	Gx = (gyro_x / 131.0) - GxCal
	Gy = (gyro_y / 131.0) - GyCal
	Gz = (gyro_z / 131.0) - GzCal
	

	print ("Gx=%.2f" %Gx, u'\u00b0'+ "/s", "\tGy=%.2f" %Gy, u'\u00b0'+ "/s", "\tGz=%.2f" %Gz, u'\u00b0'+ "/s", "\tAx=%.2f g" %Ax, "\tAy=%.2f g" %Ay, "\tAz=%.2f g" %Az) 	
	sleep(0.5)
