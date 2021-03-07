//----------------------------------------------------------------------
// Copyright (c) 2020, gcarver
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
// FILE    gy521.cpp
// BY      gcarver
// DATE    09/20/2020 09:33 PM
//----------------------------------------------------------------------

//Module to handle communication with the gy521 6 axis accelerometer
// This controller communicates using I2C.

#include <iostream>
#include <cmath>
#include <unistd.h>
#include <errno.h>
#include <wiringPiI2C.h>
#include <wiringPi.h>

namespace
{
	constexpr uint32_t _ADDRESS = 0x68;			// 0x69 is also possible
	constexpr uint32_t CALIBRATE_COUNT = 500;
	constexpr float ACCEL_FACTOR = 4096.0f;
	constexpr float GYRO_FACTOR = 65.5f;
	constexpr float TODEG = 180.0f / 3.14159265f;

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

	constexpr uint32_t _DEFAULTFREQ = 100;

}	//namespace

//--------------------------------------------------------
class gy521
{
public:

	//--------------------------------------------------------
	gy521( bool bHigh = false )
	{
		uint32_t a = _ADDRESS + (bHigh ? 1 : 0);
		_i2c = wiringPiI2CSetup(a);				// If this is -1 an error occurred.
		delayMicroseconds(50);					// Wait for init to settle.
		bGood = _i2c >= 0;

		SetClockSource(CLOCK_PLL_XGYRO);
		SetFullScaleGyroRange(GYRO_FS_250);
		SetFullScaleAccelRange(ACCEL_FS_2);
		SetSleepEnabled(false);

		_instance = this;						// We currently only support 1 instance of this object.
		Calibrate();
	}

	//--------------------------------------------------------
	~gy521(  )
	{
		close(_i2c);
		_instance = nullptr;
	}

	//--------------------------------------------------------
	static gy521 *QInstance(  ) { return _instance; }

	//--------------------------------------------------------
	bool QGood( ) const { return bGood; }

	//--------------------------------------------------------
	void SetClockSource( uint8_t aSource )
	{
		_writebits(RA_PWR_MGMT_1, PWR1_CLKSEL_BIT, PWR1_CLKSEL_LENGTH, aSource);
	}

	//--------------------------------------------------------
	void SetFullScaleGyroRange( uint8_t aRange )
	{
		_writebits(RA_GYRO_CONFIG, GCONFIG_FS_SEL_BIT, GCONFIG_FS_SEL_LENGTH, aRange);
	}

	//--------------------------------------------------------
	void SetFullScaleAccelRange( uint8_t aRange )
	{
		_writebits(RA_ACCEL_CONFIG, ACONFIG_AFS_SEL_BIT, ACONFIG_AFS_SEL_LENGTH, aRange);
	}

	//--------------------------------------------------------
	void SetSleepEnabled( bool aTF )
	{
		_writebits(RA_PWR_MGMT_1, PWR1_SLEEP_BIT, 1, aTF);
	}

	//--------------------------------------------------------
	const float *GetAccelTempRot(  )
	{
		auto pdata = _readbuffer(RA_ACCEL_XOUT_H, 7);
		uint32_t i = 0;
		for ( ; i < 3; ++i) {
			pdata[i] = (pdata[i] - _Adj[i]) / ACCEL_FACTOR;
		}
		++i;									// Skip temperature.
		for ( ; i < 7; ++i) {
			pdata[i] = (pdata[i] - _Adj[i]) / GYRO_FACTOR;
		}
		return pdata;
	}

	const float *GetRPY( float aDelta )
	{
		auto pdata = GetAccelTempRot();
		float rollangle = atan2(pdata[1], pdata[2]) * TODEG;
		float pitchangle = atan2(pdata[0], sqrt(pdata[1] * pdata[1] + pdata[2] * pdata[2])) * TODEG;

		_rpy[0] = 0.99f * (_rpy[0] + pdata[4] * aDelta) + 0.01f * rollangle;
		_rpy[1] = 0.99f * (_rpy[1] + pdata[5] * aDelta) + 0.01f * pitchangle;
		_rpy[2] = pdata[6];
		return _rpy;
	}

	//--------------------------------------------------------
	const float *GetAcceleration(  )
	{
		auto pdata = _readbuffer(RA_ACCEL_XOUT_H, 3);
		for ( uint32_t i = 0; i < 3; ++i) {
			pdata[i] = (pdata[i] - _Adj[i]) / ACCEL_FACTOR;
		}
		return pdata;
	}

	//--------------------------------------------------------
	const float *GetRotation(  )
	{
		auto pdata = _readbuffer(RA_GYRO_XOUT_H, 3);
		for ( uint32_t i = 0; i < 3; ++i) {
			pdata[i] = (pdata[i] - _Adj[4 + i]) / GYRO_FACTOR;
		}
		return pdata;
	}

	//--------------------------------------------------------
	void Reset(  )
	{
		_writebits(RA_PWR_MGMT_1, PWR1_DEVICE_RESET_BIT, 1, 1);
	}

private:
	int32_t _i2c = 0;
	float _buffer[8];
	float _Adj[8];
	float _rpy[3] = {0.0f, 0.0f, 0.0f};
	bool bGood = true;

	static gy521 *_instance;

	//--------------------------------------------------------
	// Read 8 bit value and return.
	const int32_t _read8( uint32_t aLoc )
	{
		int32_t ret = wiringPiI2CReadReg8(_i2c, aLoc);
		//If the value is <0 it's a read error.
		return ret >= 0 ? ret : 0;
	}

	//--------------------------------------------------------
	// Read 16 bit value and return.
	const int32_t _read16( uint32_t aLoc )
	{
		int32_t ret = wiringPiI2CReadReg16(_i2c, aLoc);
		return ret >= 0 ? ret : 0;
	}

	//--------------------------------------------------------
	float *_readbuffer( uint32_t aLoc, uint32_t aCount )
	{
		for ( uint32_t i = 0; i < aCount; ++i) {
			auto v = _read16(aLoc + i * 2);
			v = ((v & 0xFF) << 8) | ((v >> 8) & 0xFF);
			//Set the value but endian convert it 1st
			_buffer[i] = utof(v);
		}
		return _buffer;
	}

	//--------------------------------------------------------
	const uint8_t _readbits( uint32_t aLoc, uint8_t aBit, uint8_t aLen )
	{
		uint8_t v = _read8(aLoc);
		return (v >> (aBit - aLen + 1)) & ((1 << aLen) - 1);
	}

	//--------------------------------------------------------
	// Write 8 bit integer aVal to given address aLoc.
	int32_t _write8( uint8_t aValue, uint32_t aLoc )
	{
		return wiringPiI2CWriteReg8(_i2c, aLoc, aValue);
	}

	//--------------------------------------------------------
	void _writebits( uint32_t aLoc, uint8_t aBit, uint8_t aLen, uint8_t aValue )
	{
		uint8_t v = _read8(aLoc);
		uint8_t mask = ((1 << aLen) - 1) << (aBit - aLen + 1);
		uint8_t tmp = (v << (aBit - aLen + 1)) & mask;
		tmp &= ~mask;
		tmp |= aValue;
		_write8(tmp, aLoc);
	}

	//--------------------------------------------------------
	static float utof( int32_t aValue )
	{
// 		if (aValue >= 0x8000) {
// 			aValue = -((65535 - aValue) + 1);
// 		}
		return static_cast<float>(aValue);
	}

	//--------------------------------------------------------
	void Calibrate(  )
	{
		for ( auto &v : _Adj ) {
			v = 0.0f;
		}

		for ( uint32_t i = 0; i < CALIBRATE_COUNT; ++i) {
			auto pdata = GetAccelTempRot();
			uint32_t j = 0;
			for ( auto &v : _Adj ) {
				v += pdata[j++];
			}
			delayMicroseconds(5);
		}

		for ( auto &v : _Adj ) {
			v /= static_cast<float>(CALIBRATE_COUNT);
		}

		//Don't adjust temperature.
		_Adj[3] = 0.0f;
	}
};

gy521 *gy521::_instance = nullptr;

//Following are the 8th interface functions.
extern "C"
{

//--------------------------------------------------------
bool Startup(  )
{
	if (!gy521::QInstance()) {
		auto p = new gy521();
	}
	return gy521::QInstance()->QGood();
}

//--------------------------------------------------------
bool IsGood(  )
{
	auto p = gy521::QInstance();
	return p ? p->QGood() : false;
}

//--------------------------------------------------------
void Shutdown(  )
{
	auto p = gy521::QInstance();
	if (p) {
		delete p;
	}
}

//--------------------------------------------------------
const float *GetAccelTempRot(  )
{
	const float *d = nullptr;
	auto p = gy521::QInstance();
	if (p) {
		d = p->GetAccelTempRot();
	}
	return d;
}

//--------------------------------------------------------
const float *GetAcceleration(  )
{
	const float *d = nullptr;
	auto p = gy521::QInstance();
	if (p) {
		d = p->GetAcceleration();
	}
	return d;
}

//--------------------------------------------------------
const float *GetRotation(  )
{
	const float *d = nullptr;
	auto p = gy521::QInstance();
	if (p) {
		d = p->GetRotation();
	}
	return d;
}

//--------------------------------------------------------
const float *GetRPY( float aDelta )
{
	const float *d = nullptr;
	auto p = gy521::QInstance();
	if (p) {
		d = p->GetRPY(aDelta);
	}
	return d;
}

//--------------------------------------------------------
void Reset(  )
{
	auto p = gy521::QInstance();
	if (p) {
		p->Reset();
	}
}

} //extern C
