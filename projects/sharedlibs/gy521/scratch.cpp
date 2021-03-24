
#include <iostream>
#include <cmath>
#include <unistd.h>
#include <errno.h>
#include <wiringPiI2C.h>
#include <wiringPi.h>

double accelX,accelY,accelZ,temperature,gyroX,gyroY,gyroZ,gyro_x_cal,gyro_y_cal,gyro_z_cal; //These will be the raw data from the MPU6050.
int32_t _i2c = 0;
uint32_t timer; //it's a timer, saved as a big-ass unsigned int.  We use it to save times from the "micros()" command and subtract the present time in microseconds from the time stored in timer to calculate the time for each loop.
double roll, pitch ,yaw; //These are the angles in the complementary filter
float rollangle,pitchangle;
int cal_int;

void setup() {
  // Set up MPU 6050:
  _i2c = wiringPiI2CSetup(a);				// If this is -1 an error occurred.

  for(cal_int=1;cal_int<=2000;cal_int++)
  {
   recordRegisters();
   gyro_x_cal += gyroX;
   gyro_y_cal  += gyroY ;
   gyro_z_cal += gyroZ;
  }
  gyro_x_cal /= 2000;
  gyro_y_cal /= 2000;
  gyro_z_cal /= 2000;
 
  //start a timer
  timer = micros();
}

void loop() {
//Now begins the main loop.
  //Collect raw data from the sensor.
  recordRegisters();
  gyroX = gyroX / 65.5;
  gyroY = gyroY / 65.5;
  gyroZ = gyroZ / 65.5;

  accelX = accelX / 4096.0;
  accelY = accelY / 4096.0;
  accelZ= accelZ / 4096.0;
 
  double dt = (double)(micros() - timer) / 1000000; //This line does three things: 1) stops the timer, 2)converts the timer's output to seconds from microseconds, 3)casts the value as a double saved to "dt".
  timer = micros(); //start the timer again so that we can calculate the next dt.

  //the next two lines calculate the orientation of the accelerometer relative to the earth and convert the output of atan2 from radians to degrees
  //We will use this data to correct any cumulative errors in the orientation that the gyroscope develops.
  rollangle=atan2(accelY,accelZ)*180/PI; // FORMULA FOUND ON INTERNET
  pitchangle=atan2(accelX,sqrt(accelY*accelY+accelZ*accelZ))*180/PI; //FORMULA FOUND ON INTERNET

  //THE COMPLEMENTARY FILTER
  //This filter calculates the angle based MOSTLY on integrating the angular velocity to an angular displacement.
  //dt, recall, is the time between gathering data from the MPU6050.  We'll pretend that the
  //angular velocity has remained constant over the time dt, and multiply angular velocity by
  //time to get displacement.
  //The filter then adds a small correcting factor from the accelerometer ("roll" or "pitch"), so the gyroscope knows which way is down.
  roll = 0.99 * (roll+ gyroX * dt) + 0.01 * rollangle; // Calculate the angle using a Complimentary filter
  pitch = 0.99 * (pitch + gyroY * dt) + 0.01 * pitchangle;
  yaw=gyroZ;
 
  std::cout << "roll  " << roll;
  std::cout << "   pitch  " << pitch;
  std::cout << "   yaw    " << yaw;
}

void setupMPU(){
  wiringPiI2CWriteReg8(_i2c, 0x6B, 0); //Setting SLEEP register to 0. (Required; see Note on p. 9)
  wiringPiI2CWriteReg8(_i2c, 0x1B, 0x08);
//  Wire.write(0x1B); //Accessing the register 1B - Gyroscope Configuration (Sec. 4.4)
//  Wire.write(0x08); //Setting the gyro to full scale +/- 500deg./s
  wiringPiI2CWriteReg8(_i2c, 0x1C, 0x10);
//   Wire.write(0x1C); //Accessing the register 1C - Acccelerometer Configuration (Sec. 4.5)
//   Wire.write(0x10); //Setting the accel to +/- 8g

  wiringPiI2CWriteReg8(_i2c, 0x1A, 0x03);
}

void recordRegisters() {

  int32_t ret = wiringPiI2CReadReg8(_i2c, 0x3B) << 8;
  accelX = ret | wiringPiI2CReadReg8(_i2c, 0x3C);

  ret = wiringPiI2CReadReg8(_i2c, 0x3D) << 8;
  accelY = ret | wiringPiI2CReadReg8(_i2c, 0x3E);

  ret = wiringPiI2CReadReg8(_i2c, 0x3F) << 8;
  accelZ = ret | wiringPiI2CReadReg8(_i2c, 0x40);

  ret = wiringPiI2CReadReg8(_i2c, 0x43) << 8;
  gyroX = ret | wiringPiI2CReadReg8(_i2c, 0x44);
  ret = wiringPiI2CReadReg8(_i2c, 0x45) << 8;
  gyroY = ret | wiringPiI2CReadReg8(_i2c, 0x46);
  ret = wiringPiI2CReadReg8(_i2c, 0x47) << 8;
  gyroZ = ret | wiringPiI2CReadReg8(_i2c, 0x48);

  if(cal_int == 2000)
  {
    gyroX -= gyro_x_cal;
    gyroY -= gyro_y_cal;
    gyroZ -= gyro_z_cal;
  }
}

int32_t main(  )
{
	setup();
	loop();
	return 0;
}