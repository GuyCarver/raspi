
//Module for filtering mpu9250 data and outputing fairly stable yaw/pitch/roll.
// See: https://x-io.co.uk/open-source-imu-and-ahrs-algorithms/

#include <math.h>
#include <iostream>

namespace
{

float sampleFreq = 512.0f;
float quat[4] = { 1.0f, 0.0f, 0.0f, 0.0f };
float ypr[3] = { 0.0f, 0.0f, 0.0f };

///---------------------------------------------------------------------------------------------------
/// Fast inverse square-root
/// See: http://en.wikipedia.org/wiki/Fast_inverse_square_root
float invSqrt( float aX )
{
	float halfx = 0.5f * aX;
	float y = aX;
	long i = *reinterpret_cast<long*>(&y);
	i = 0x5f3759df - (i >> 1);
	y = *reinterpret_cast<float*>(&i);
	y = y * (1.5f - (halfx * y * y));
	return y;
}

///---------------------------------------------------------------------------------------------------
/// Gyro/Accel algorithm update
float *UpdateGA( float gx, float gy, float gz, float ax, float ay, float az, float dt )
{
	float recipNorm;
	float s[4];
	float qDot[4];
	float _2q0, _2q1, _2q2, _2q3, _4q0, _4q1, _4q2 ,_8q1, _8q2, q0q0, q1q1, q2q2, q3q3;

	// Rate of change of quaternion from gyroscope
	qDot[0] = 0.5f * (-quat[1] * gx - quat[2] * gy - quat[3] * gz);
	qDot[1] = 0.5f * (quat[0] * gx + quat[2] * gz - quat[3] * gy);
	qDot[2] = 0.5f * (quat[0] * gy - quat[1] * gz + quat[3] * gx);
	qDot[3] = 0.5f * (quat[0] * gz + quat[1] * gy - quat[2] * gx);

	// Compute feedback only if accelerometer measurement valid (avoids NaN in accelerometer normalisation)
	if(!((ax == 0.0f) && (ay == 0.0f) && (az == 0.0f))) {

		// Normalise accelerometer measurement
		recipNorm = invSqrt(ax * ax + ay * ay + az * az);
		ax *= recipNorm;
		ay *= recipNorm;
		az *= recipNorm;

		// Auxiliary variables to avoid repeated arithmetic
		_2q0 = 2.0f * quat[0];
		_2q1 = 2.0f * quat[1];
		_2q2 = 2.0f * quat[2];
		_2q3 = 2.0f * quat[3];
		_4q0 = 4.0f * quat[0];
		_4q1 = 4.0f * quat[1];
		_4q2 = 4.0f * quat[2];
		_8q1 = 8.0f * quat[1];
		_8q2 = 8.0f * quat[2];
		q0q0 = quat[0] * quat[0];
		q1q1 = quat[1] * quat[1];
		q2q2 = quat[2] * quat[2];
		q3q3 = quat[3] * quat[3];

		// Gradient decent algorithm corrective step
		s[0] = _4q0 * q2q2 + _2q2 * ax + _4q0 * q1q1 - _2q1 * ay;
		s[1] = _4q1 * q3q3 - _2q3 * ax + 4.0f * q0q0 * quat[1] - _2q0 * ay - _4q1 + _8q1 * q1q1 + _8q1 * q2q2 + _4q1 * az;
		s[2] = 4.0f * q0q0 * quat[2] + _2q0 * ax + _4q2 * q3q3 - _2q3 * ay - _4q2 + _8q2 * q1q1 + _8q2 * q2q2 + _4q2 * az;
		s[3] = 4.0f * q1q1 * quat[3] - _2q1 * ax + 4.0f * q2q2 * quat[3] - _2q2 * ay;
		recipNorm = invSqrt(s[0] * s[0] + s[1] * s[1] + s[2] * s[2] + s[3] * s[3]); // normalise step magnitude
		s[0] *= recipNorm;
		s[1] *= recipNorm;
		s[2] *= recipNorm;
		s[3] *= recipNorm;

		// Apply feedback step
		qDot[0] -= dt * s[0];
		qDot[1] -= dt * s[1];
		qDot[2] -= dt * s[2];
		qDot[3] -= dt * s[3];
	}

	// Integrate rate of change of quaternion to yield quaternion
	auto sf = 1.0f / sampleFreq;
	quat[0] += qDot[0] * sf;
	quat[1] += qDot[1] * sf;
	quat[2] += qDot[2] * sf;
	quat[3] += qDot[3] * sf;

	// Normalise quaternion
	recipNorm = invSqrt(quat[0] * quat[0] + quat[1] * quat[1] + quat[2] * quat[2] + quat[3] * quat[3]);
	quat[0] *= recipNorm;
	quat[1] *= recipNorm;
	quat[2] *= recipNorm;
	quat[3] *= recipNorm;

	return quat;
}

}

extern "C"
{

///---------------------------------------------------------------------------------------------------
/// AHRS algorithm update
float *Update( float gx, float gy, float gz, float ax, float ay, float az, float mx, float my, float mz, float dt )
{
	float recipNorm;
	float s[4];
	float qDot[4];
	float hx, hy;
	float _2q0mx, _2q0my, _2q0mz, _2q1mx, _2bx, _2bz, _4bx, _4bz, _2q0, _2q1, _2q2, _2q3, _2q0q2, _2q2q3, q0q0, q0q1, q0q2, q0q3, q1q1, q1q2, q1q3, q2q2, q2q3, q3q3;

	// Use IMU algorithm if magnetometer measurement invalid (avoids NaN in magnetometer normalisation)
	if((mx == 0.0f) && (my == 0.0f) && (mz == 0.0f)) {
// 		std::cout << "UpdateGA" << std::endl;
		return UpdateGA(gx, gy, gz, ax, ay, az, dt);
	}

	// Rate of change of quaternion from gyroscope
	qDot[0] = 0.5f * (-quat[1] * gx - quat[2] * gy - quat[3] * gz);
	qDot[1] = 0.5f * (quat[0] * gx + quat[2] * gz - quat[3] * gy);
	qDot[2] = 0.5f * (quat[0] * gy - quat[1] * gz + quat[3] * gx);
	qDot[3] = 0.5f * (quat[0] * gz + quat[1] * gy - quat[2] * gx);

// 	std::cout << "gx" << gx << "gy" << gy << "gz" << gz
// 		<< "ax" << ax << "ay" << ay << "az" << az << "mx" << mx << "my" << my << "mz" << mz << std::endl;

	// Compute feedback only if accelerometer measurement valid (avoids NaN in accelerometer normalisation)
	if(!((ax == 0.0f) && (ay == 0.0f) && (az == 0.0f))) {

		// Normalise accelerometer measurement
		recipNorm = invSqrt(ax * ax + ay * ay + az * az);
		ax *= recipNorm;
		ay *= recipNorm;
		az *= recipNorm;

		// Normalise magnetometer measurement
		recipNorm = invSqrt(mx * mx + my * my + mz * mz);
		mx *= recipNorm;
		my *= recipNorm;
		mz *= recipNorm;

		// Auxiliary variables to avoid repeated arithmetic
		_2q0mx = 2.0f * quat[0] * mx;
		_2q0my = 2.0f * quat[0] * my;
		_2q0mz = 2.0f * quat[0] * mz;
		_2q1mx = 2.0f * quat[1] * mx;
		_2q0 = 2.0f * quat[0];
		_2q1 = 2.0f * quat[1];
		_2q2 = 2.0f * quat[2];
		_2q3 = 2.0f * quat[3];
		_2q0q2 = 2.0f * quat[0] * quat[2];
		_2q2q3 = 2.0f * quat[2] * quat[3];
		q0q0 = quat[0] * quat[0];
		q0q1 = quat[0] * quat[1];
		q0q2 = quat[0] * quat[2];
		q0q3 = quat[0] * quat[3];
		q1q1 = quat[1] * quat[1];
		q1q2 = quat[1] * quat[2];
		q1q3 = quat[1] * quat[3];
		q2q2 = quat[2] * quat[2];
		q2q3 = quat[2] * quat[3];
		q3q3 = quat[3] * quat[3];

		// Reference direction of Earth's magnetic field
		hx = mx * q0q0 - _2q0my * quat[3] + _2q0mz * quat[2] + mx * q1q1 + _2q1 * my * quat[2] + _2q1 * mz * quat[3] - mx * q2q2 - mx * q3q3;
		hy = _2q0mx * quat[3] + my * q0q0 - _2q0mz * quat[1] + _2q1mx * quat[2] - my * q1q1 + my * q2q2 + _2q2 * mz * quat[3] - my * q3q3;
		_2bx = sqrt(hx * hx + hy * hy);
		_2bz = -_2q0mx * quat[2] + _2q0my * quat[1] + mz * q0q0 + _2q1mx * quat[3] - mz * q1q1 + _2q2 * my * quat[3] - mz * q2q2 + mz * q3q3;
		_4bx = 2.0f * _2bx;
		_4bz = 2.0f * _2bz;

		// Gradient decent algorithm corrective step
		s[0] = -_2q2 * (2.0f * q1q3 - _2q0q2 - ax) + _2q1 * (2.0f * q0q1 + _2q2q3 - ay) - _2bz * quat[2] * (_2bx * (0.5f - q2q2 - q3q3) + _2bz * (q1q3 - q0q2) - mx) + (-_2bx * quat[3] + _2bz * quat[1]) * (_2bx * (q1q2 - q0q3) + _2bz * (q0q1 + q2q3) - my) + _2bx * quat[2] * (_2bx * (q0q2 + q1q3) + _2bz * (0.5f - q1q1 - q2q2) - mz);
		s[1] = _2q3 * (2.0f * q1q3 - _2q0q2 - ax) + _2q0 * (2.0f * q0q1 + _2q2q3 - ay) - 4.0f * quat[1] * (1 - 2.0f * q1q1 - 2.0f * q2q2 - az) + _2bz * quat[3] * (_2bx * (0.5f - q2q2 - q3q3) + _2bz * (q1q3 - q0q2) - mx) + (_2bx * quat[2] + _2bz * quat[0]) * (_2bx * (q1q2 - q0q3) + _2bz * (q0q1 + q2q3) - my) + (_2bx * quat[3] - _4bz * quat[1]) * (_2bx * (q0q2 + q1q3) + _2bz * (0.5f - q1q1 - q2q2) - mz);
		s[2] = -_2q0 * (2.0f * q1q3 - _2q0q2 - ax) + _2q3 * (2.0f * q0q1 + _2q2q3 - ay) - 4.0f * quat[2] * (1 - 2.0f * q1q1 - 2.0f * q2q2 - az) + (-_4bx * quat[2] - _2bz * quat[0]) * (_2bx * (0.5f - q2q2 - q3q3) + _2bz * (q1q3 - q0q2) - mx) + (_2bx * quat[1] + _2bz * quat[3]) * (_2bx * (q1q2 - q0q3) + _2bz * (q0q1 + q2q3) - my) + (_2bx * quat[0] - _4bz * quat[2]) * (_2bx * (q0q2 + q1q3) + _2bz * (0.5f - q1q1 - q2q2) - mz);
		s[3] = _2q1 * (2.0f * q1q3 - _2q0q2 - ax) + _2q2 * (2.0f * q0q1 + _2q2q3 - ay) + (-_4bx * quat[3] + _2bz * quat[1]) * (_2bx * (0.5f - q2q2 - q3q3) + _2bz * (q1q3 - q0q2) - mx) + (-_2bx * quat[0] + _2bz * quat[2]) * (_2bx * (q1q2 - q0q3) + _2bz * (q0q1 + q2q3) - my) + _2bx * quat[1] * (_2bx * (q0q2 + q1q3) + _2bz * (0.5f - q1q1 - q2q2) - mz);
		recipNorm = invSqrt(s[0] * s[0] + s[1] * s[1] + s[2] * s[2] + s[3] * s[3]); // normalise step magnitude
		s[0] *= recipNorm;
		s[1] *= recipNorm;
		s[2] *= recipNorm;
		s[3] *= recipNorm;

		// Apply feedback step
		qDot[0] -= dt * s[0];
		qDot[1] -= dt * s[1];
		qDot[2] -= dt * s[2];
		qDot[3] -= dt * s[3];
	}

	// Integrate rate of change of quaternion to yield quaternion
	auto sf = 1.0f / sampleFreq;
	quat[0] += qDot[0] * sf;
	quat[1] += qDot[1] * sf;
	quat[2] += qDot[2] * sf;
	quat[3] += qDot[3] * sf;

	// Normalise quaternion
	recipNorm = invSqrt(quat[0] * quat[0] + quat[1] * quat[1] + quat[2] * quat[2] + quat[3] * quat[3]);
	quat[0] *= recipNorm;
	quat[1] *= recipNorm;
	quat[2] *= recipNorm;
	quat[3] *= recipNorm;

	return quat;
}

float *UpdateYPR( float gx, float gy, float gz, float ax, float ay, float az, float mx, float my, float mz, float dt )
{
	auto pq = Update(gx, gy, gz, ax, ay, az, mx, my, mz, dt);
// 	std::cout << "0 " << pq[0] << " 1 " << pq[1] << " 2 " << pq[2] << " 3 " << pq[3] << std::endl;
	ypr[0] = atan2(2.0f * (pq[1] * pq[2] + pq[0] * pq[3]), pq[0] * pq[0] + pq[1] * pq[1] - pq[2] * pq[2] - pq[3] * pq[3]);
	ypr[1] = -asin(2.0f * (pq[1] * pq[3] - pq[0] * pq[2]));
	ypr[2] = atan2(2.0f * (pq[0] * pq[1] + pq[2] * pq[3]), pq[0] * pq[0] - pq[1] * pq[1] - pq[2] * pq[2] + pq[3] * pq[3]);

	return ypr;
}

void SetSampleFreq( float aFreq )
{
	sampleFreq = aFreq;
}

} //extern "C"
