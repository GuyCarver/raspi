//----------------------------------------------------------------------
// Copyright (c) 2021, gcarver
// All rights reserved.
//
// Redistribution and use in source and binary forms, with or without modification,
// are permitted provided that the following conditions are met:
//
//     * Redistributions of source code must retain the above copyright notice,
//       this list of conditions and the following disclaimer.
//
//     * Redistributions in binary form must reproduce the above copyright notice,
//       this list of conditions and the following disclaimer in the documentation
//       and/or other materials provided with the distribution.
//
//     * The name of Guy Carver may not be used to endorse or promote products derived
//       from this software without specific prior written permission.
//
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
// ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
// WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
// DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
// ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
// (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
// LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
// ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
// (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
// SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
//
// FILE    mpu9250.cpp
// BY      gcarver
// DATE    01/25/2021 09:00 AM
//----------------------------------------------------------------------

//Module to handle communication with the mpu9850 9 axis accelerometer
// This controller communicates using I2C.  This board has an mpu-9250 and gy-6500

#include <iostream>
#include <cmath>
#include <unistd.h>
#include <errno.h>
#include <wiringPiI2C.h>
#include <wiringPi.h>
#include <thread>
#include <mutex>

// Possibly move all initialization into the background thread?
// Lock data reading from the main thread?
// Move mwick into here.

namespace
{
	constexpr uint32_t _ADDRESS = 0x68;			// gy-6500 address.
	constexpr uint32_t CALIBRATE_COUNT = 250;
	constexpr float ACCEL_FACTOR = (1.0f / 4096.0f);
	constexpr float GYRO_FACTOR = (1.0f / 65.5f);

	constexpr uint32_t CLOCK_PLL_XGYRO = 0x01;
	constexpr uint32_t GYRO_FS_250 = 0x00;
	constexpr uint32_t ACCEL_FS_2 = 0x00;

	constexpr uint32_t RA_SMPLRT_DIV   = 0x19;
	constexpr uint32_t RA_CONFIG       = 0x1A;
	constexpr uint32_t RA_GYRO_CONFIG  = 0x1B;
	constexpr uint32_t RA_ACCEL_CONFIG = 0x1C;
	constexpr uint32_t RA_INT_ENABLE   = 0x38;
	constexpr uint32_t RA_ACCEL_XOUT_H = 0x3B;
	constexpr uint32_t RA_ACCEL_YOUT_H = 0x3D;
	constexpr uint32_t RA_ACCEL_ZOUT_H = 0x3F;
	constexpr uint32_t RA_GYRO_XOUT_H  = 0x43;
	constexpr uint32_t RA_GYRO_YOUT_H  = 0x45;
	constexpr uint32_t RA_GYRO_ZOUT_H  = 0x47;

	constexpr uint32_t RA_PWR_MGMT_1 = 0x6B;

	constexpr uint8_t PWR1_DEVICE_RESET_BIT = 7;
	constexpr uint8_t PWR1_SLEEP_BIT  = 6;
	constexpr uint8_t PWR1_CLKSEL_BIT = 2;
	constexpr uint8_t PWR1_CLKSEL_LENGTH = 3;

	constexpr uint8_t GCONFIG_FS_SEL_BIT    = 4;
	constexpr uint8_t GCONFIG_FS_SEL_LENGTH = 2;

	constexpr uint8_t ACONFIG_AFS_SEL_BIT    = 4;
	constexpr uint8_t ACONFIG_AFS_SEL_LENGTH = 2;

// 	constexpr uint32_t _LED0_ON_H = 0x7;
// 	constexpr uint32_t _LED0_OFF_L = 0x8;
// 	constexpr uint32_t _LED0_OFF_H = 0x9;
// 	constexpr uint32_t _ALLLED_ON_L = 0xFA;
// 	constexpr uint32_t _ALLLED_ON_H = 0xFB;
// 	constexpr uint32_t _ALLLED_OFF_L = 0xFC;
// 	constexpr uint32_t _ALLLED_OFF_H = 0xFD;


//--------------------------------------------------------
	constexpr uint32_t _ADDRESS_AK = 0x0C;		// gy-9250 address.

	constexpr uint32_t AK_ST1 = 0x02;
	constexpr uint32_t AK_ST2 = 0x09;
	constexpr uint32_t AK_CNTL = 0x0A;
	constexpr uint32_t AK_HX = 0x03;
	constexpr uint32_t AK_AX = 0x10;

	constexpr uint32_t MODE_FUSE_ROM_ACCESS = 0x0F;
	constexpr float MAG_SENSE = 4900.0f;

	constexpr uint32_t _DEFAULTFREQ = 100;
}	//namespace

//--------------------------------------------------------
class mpu9250
{
public:

	//--------------------------------------------------------
	mpu9250( bool bHigh = false )
	{
		_pinstance = this;

		_i2cak = wiringPiI2CSetup(_ADDRESS_AK);	// If this is -1 an error occurred.

		uint32_t a = _ADDRESS + (bHigh ? 1 : 0);
		_i2cgy = wiringPiI2CSetup(a);			// If this is -1 an error occurred.
		delayMicroseconds(50);					// Wait for init to settle.

// 		_write8(_i2cgy, 0, RA_SMPLRT_DIV);		// Set sample rate to 8hkz/1+0 for stability.
// 		delayMicroseconds(50);
// 		_write8(_i2cgy, 1, RA_PWR_MGMT_1);
// 		delayMicroseconds(50);
// 		_write8(_i2cgy, 0, RA_CONFIG);
// 		delayMicroseconds(50);
// 		_write8(_i2cgy, 0, RA_GYRO_CONFIG);
// 		delayMicroseconds(50);
// 		_write8(_i2cgy, 0, RA_ACCEL_CONFIG);
// 		delayMicroseconds(50);
// 		_write8(_i2cgy, 1, RA_INT_ENABLE);
// 		delayMicroseconds(50);

 		_write8(_i2cgy, 0, RA_SMPLRT_DIV);		// Set sample rate to 8hkz/1+0 for stability.
		delayMicroseconds(50);					// Wait for init to settle.
		_write8(_i2cgy, 0, RA_PWR_MGMT_1);
		delayMicroseconds(50);
		_write8(_i2cgy, 1, RA_PWR_MGMT_1);
		delayMicroseconds(50);
		_write8(_i2cgy, 3, RA_CONFIG);
		delayMicroseconds(50);
		_write8(_i2cgy, 16, RA_GYRO_CONFIG);
		delayMicroseconds(50);
		_write8(_i2cgy, 16, RA_ACCEL_CONFIG);
		delayMicroseconds(50);

		auto makemagadj = []( int32_t aVal ) {
			return ((aVal - 128) / 256.0f) + 1.0f;
		};

		_write8(_i2cak, 0, AK_CNTL);
		delayMicroseconds(100);
		_write8(_i2cak, MODE_FUSE_ROM_ACCESS, AK_CNTL);
		delayMicroseconds(100);
		_magadj[0] = makemagadj(wiringPiI2CReadReg8(_i2cak, AK_AX));
		_magadj[1] = makemagadj(wiringPiI2CReadReg8(_i2cak, AK_AX + 1));
		_magadj[2] = makemagadj(wiringPiI2CReadReg8(_i2cak, AK_AX + 2));
// 		std::cout << _magadj[0] << ", " << _magadj[1] << ", " << _magadj[2] << std::endl;
		_write8(_i2cak, 0, AK_CNTL);
		delayMicroseconds(100);
		_write8(_i2cak, 0x16, AK_CNTL);

		_pLoop = new std::thread([] () { _pinstance->MainLoop(); });
	}

	//--------------------------------------------------------
	~mpu9250(  )
	{
		bRunning = false;						// Turn off loop.
		Suspend(false);							// Make sure we haven't suspending the BG thread.
		_pLoop->join();							// Wait for _pLoop to exit.
		delete _pLoop;
		close(_i2cgy);
		close(_i2cak);
		_pinstance = nullptr;
	}

	static mpu9250 *QInstance(  ) { return _pinstance; }

	//--------------------------------------------------------
	void Suspend( bool abTF )
	{
		if (abTF) {
			if (!bSuspended) {
				bSuspended = true;
				_suspend.lock();
			}
		}
		else if (bSuspended) {
			bSuspended = false;
			_suspend.unlock();
		}
	}

	//--------------------------------------------------------
	const float *GetAccelTempRot(  )
	{
		//Might want to lock before reading.
		return _atp;
	}

	//--------------------------------------------------------
	const float *GetMag(  )
	{
		//Might want to lock before reading.
		return _mag;
	}

private:
	std::thread *_pLoop = nullptr;
	std::mutex _suspend;
	int32_t _i2cgy = 0;							// gy-6500
	int32_t _i2cak = 0;							// gy-9250
	float _buffer[8];
	float _adj[8];
	float _atp[8] = {0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f};
	float _mag[3] = {0.0f, 0.0f, 0.0f};
	float _magadj[3];
	float timer = 0.0f;
	bool bRunning = true;
	bool bSuspended = false;

	static mpu9250 *_pinstance;

	//--------------------------------------------------------
	// Read 16 bit value and return.
	const int32_t _read16( uint32_t aAddress, uint32_t aLoc )
	{
		int8_t vh = wiringPiI2CReadReg8(aAddress, aLoc);
		int8_t vl = wiringPiI2CReadReg8(aAddress, aLoc + 1);
		return (vh << 8) | (vl & 0xFF);
	}

	//--------------------------------------------------------
	float *_readbuffer( uint32_t aAddress, uint32_t aLoc, uint32_t aCount )
	{
		for ( uint32_t i = 0; i < aCount; ++i) {
			auto v = _read16(aAddress, aLoc + (i * 2));
			if (v > 32768) {
				v -= 65536;
			}
			_buffer[i] = static_cast<float>(v);
		}
		return _buffer;
	}

	//--------------------------------------------------------
	// Write 8 bit integer aVal to given address aLoc.
	int32_t _write8( uint32_t aAddress, uint8_t aValue, uint32_t aLoc )
	{
		return wiringPiI2CWriteReg8(aAddress, aLoc, aValue);
	}

	//--------------------------------------------------------
	// Write array of 8 bit integer aVal to given address aLoc.
	void _writebuffer8( uint32_t aAddress, uint32_t aLoc, uint8_t *apBuffer, uint32_t aCount )
	{
		for ( uint32_t i = 0; i < aCount; ++i) {
			_write8(aAddress, aLoc++, apBuffer[i]);
		}
	}

	//--------------------------------------------------------
	void Calibrate(  )
	{
		for ( auto &v : _adj ) {
			v = 0.0f;
		}

		for ( uint32_t i = 0; i < CALIBRATE_COUNT; ++i) {
			UpdateAccelTempRot();
			auto pdata = GetAccelTempRot();
			uint32_t j = 0;
			for ( auto &v : _adj ) {
				v += pdata[j++];
			}
			delayMicroseconds(50);
		}

		for ( auto &v : _adj ) {
			v /= static_cast<float>(CALIBRATE_COUNT);
		}

		//Don't adjust temperature.
		_adj[3] = 0.0f;
	}

	//--------------------------------------------------------
	void UpdateAccelTempRot(  )
	{
		auto pdata = _readbuffer(_i2cgy, RA_ACCEL_XOUT_H, 7);
		uint32_t i = 0;
		for ( ; i < 3; ++i) {
			_atp[i] = pdata[i] * ACCEL_FACTOR;
		}

		//TODO: Convert this to F or C?
		_atp[i] = pdata[i++];					// Just copy the temperature over.

		for ( ; i < 7; ++i) {
			_atp[i] = pdata[i] * GYRO_FACTOR;
		}
	}

	//--------------------------------------------------------
	void UpdateMag(  )
	{
		float *pdata = nullptr;
		pdata = _readbuffer(_i2cak, AK_HX, 3);
		wiringPiI2CReadReg8(_i2cak, AK_ST2);	// Indicate we need updated readings.

		//Convert to mag data to +/-.
		for ( uint32_t i = 0; i < 3; ++i) {
			float v = pdata[i];
			_mag[i] = v * 0.149536f;	// (v / 32768) * MAG_SENSE
		}
	}

	//--------------------------------------------------------
	void MainLoop(  )
	{
		Calibrate();

		while(bRunning) {
			_suspend.lock();
			UpdateAccelTempRot();
			UpdateMag();
			_suspend.unlock();
			delayMicroseconds(33333);			// We are going to run this at 30hz.
		}
	}
};

mpu9250 *mpu9250::_pinstance = nullptr;

// int32_t main(  )
// {
// 	auto g = mpu9250();
// 	while (true) {
// 		auto m = g.GetMag();
// 		for ( uint32_t i = 0; i < 3; ++i) {
// 			std::cout << m[i] << ',';
// 		}
// 		std::cout << "                \r";
// 	}
// 	return 0;
// }

extern "C"
{

void Startup(  )
{
	if (mpu9250::QInstance() == nullptr) {
		auto p = new mpu9250();
	}
}

void Suspend( bool abTF )
{
	auto p = mpu9250::QInstance();
	if (p) {
		p->Suspend(abTF);
	}
}

void Shutdown(  )
{
	auto p = mpu9250::QInstance();
	if (p) {
		delete p;
	}
}

//--------------------------------------------------------
const float *GetAccelTempRot(  )
{
	const float *d = nullptr;
	auto p = mpu9250::QInstance();
	if (p) {
		d = p->GetAccelTempRot();
	}
	return d;
}

//--------------------------------------------------------
const float *GetMag(  )
{
	const float *d = nullptr;
	auto p = mpu9250::QInstance();
	if (p) {
		d = p->GetMag();
	}
	return d;
}

} //extern "C"
