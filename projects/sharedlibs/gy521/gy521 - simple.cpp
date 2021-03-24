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
#include <unistd.h>
#include <errno.h>
#include <wiringPiI2C.h>
#include <wiringPi.h>

namespace
{
	constexpr uint32_t _ADDRESS = 0x68;			// 0x69 is also possible
	constexpr uint32_t CALIBRATE_COUNT = 50;

	constexpr uint32_t RA_SMPLRT_DIV   = 0x19;
	constexpr uint32_t RA_CONFIG       = 0x1A;
	constexpr uint32_t RA_GYRO_CONFIG  = 0x1B;
	constexpr uint32_t RA_INT_ENABLE   = 0x38;
	constexpr uint32_t RA_ACCEL_XOUT_H = 0x3B;
	constexpr uint32_t RA_GYRO_XOUT_H  = 0x43;
	constexpr uint32_t RA_PWR_MGMT_1   = 0x6B;
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

		_write8(RA_SMPLRT_DIV, 0x07);
		_write8(RA_CONFIG, 0);
		_write8(RA_GYRO_CONFIG, 24);
		_write8(RA_INT_ENABLE, 0x01);
		_write8(RA_PWR_MGMT_1, 0x00);

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

	const int32_t *GetAccelTempRot(  )
	{
		auto pdata = _readbuffer(RA_ACCEL_XOUT_H, 7);
		for ( uint32_t i = 0; i < 7; ++i) {
			pdata[i] -= _Adj[i];
		}
		return pdata;
	}

	const int32_t *GetAccelTempRot16(  )
	{
		auto pdata = _readbuffer16(RA_ACCEL_XOUT_H, 7);
		for ( uint32_t i = 0; i < 7; ++i) {
			pdata[i] -= _Adj[i];
		}
		return pdata;
	}

	const int32_t *GetAcceleration(  )
	{
		auto pdata = _readbuffer(RA_ACCEL_XOUT_H, 3);
		for ( uint32_t i = 0; i < 3; ++i) {
			pdata[i] -= _Adj[i];
		}
		return pdata;
	}

	const int32_t *GetAcceleration16(  )
	{
		auto pdata = _readbuffer16(RA_ACCEL_XOUT_H, 3);
		for ( uint32_t i = 0; i < 3; ++i) {
			pdata[i] -= _Adj[i];
		}
		return pdata;
	}

	const int32_t *GetRotation(  )
	{
		auto pdata = _readbuffer(RA_GYRO_XOUT_H, 3);
		for ( uint32_t i = 0; i < 3; ++i) {
			pdata[i] -= _Adj[5 + i];
		}
		return pdata;
	}

	const int32_t *GetRotation16(  )
	{
		auto pdata = _readbuffer16(RA_GYRO_XOUT_H, 3);
		for ( uint32_t i = 0; i < 3; ++i) {
			pdata[i] -= _Adj[5 + i];
		}
		return pdata;
	}

//private:
	int32_t _i2c = 0;
	int32_t _buffer[8];
	int32_t _Adj[8];
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

	int32_t *_readbuffer( uint32_t aLoc, uint32_t aCount )
	{
		for ( uint32_t i = 0; i < aCount; ++i) {
			uint32_t j = i * 2;
			int32_t v = _read8(aLoc + j++) << 8;
			v |= _read8(aLoc + j);
			_buffer[i] = utoi(v);
		}
		return _buffer;
	}

	int32_t *_readbuffer16( uint32_t aLoc, uint32_t aCount )
	{
		for ( uint32_t i = 0; i < aCount; ++i) {
			int32_t v = _read16(aLoc + i * 2);
			v = ((v & 0xFF) << 8) | ((v >> 8) & 0xFF);
			//Set the value but endian convert it 1st
			_buffer[i] = utoi(v);
		}
		return _buffer;
	}

	//--------------------------------------------------------
	// Write 8 bit integer aVal to given address aLoc.
	int32_t _write8( uint8_t aValue, uint32_t aLoc )
	{
		return wiringPiI2CWriteReg8(_i2c, aLoc, aValue);
	}

	static int32_t utoi( int32_t aValue )
	{
		if (aValue >= 0x8000) {
			aValue = -((65535 - aValue) + 1);
		}
		return aValue;
	}

	void Calibrate(  )
	{
		for ( auto &v : _Adj ) {
			v = 0.0f;
		}

		for ( uint32_t i = 0; i < CALIBRATE_COUNT; ++i) {
			auto pdata = GetAccelTempRot16();
			uint32_t j = 0;
			for ( auto &v : _Adj ) {
				v += pdata[j++];
			}
			delayMicroseconds(10);
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

const int32_t *Adj(  )
{
	auto p = gy521::QInstance();
	return p->_Adj;
}

//--------------------------------------------------------
void Shutdown(  )
{
	auto p = gy521::QInstance();
	if (p) {
		delete p;
	}
}

int32_t Read8( uint32_t aIndex )
{
	auto p = gy521::QInstance();
	return p ? p->_read8(aIndex) : 0;
}

int32_t Read16( uint32_t aIndex )
{
	auto p = gy521::QInstance();
	return p ? p->_read16(aIndex) : 0;
}

const int32_t *GetAccelTempRot(  )
{
	const int32_t *d = nullptr;
	auto p = gy521::QInstance();
	if (p) {
		d = p->GetAccelTempRot();
	}
	return d;
}

const int32_t *GetAcceleration(  )
{
	const int32_t *d = nullptr;
	auto p = gy521::QInstance();
	if (p) {
		d = p->GetAcceleration();
	}
	return d;
}

const int32_t *GetRotation(  )
{
	const int32_t *d = nullptr;
	auto p = gy521::QInstance();
	if (p) {
		d = p->GetRotation();
	}
	return d;
}

const int32_t *GetAccelTempRot16(  )
{
	const int32_t *d = nullptr;
	auto p = gy521::QInstance();
	if (p) {
		d = p->GetAccelTempRot16();
	}
	return d;
}

const int32_t *GetAcceleration16(  )
{
	const int32_t *d = nullptr;
	auto p = gy521::QInstance();
	if (p) {
		d = p->GetAcceleration16();
	}
	return d;
}

const int32_t *GetRotation16(  )
{
	const int32_t *d = nullptr;
	auto p = gy521::QInstance();
	if (p) {
		d = p->GetRotation16();
	}
	return d;
}

} //extern C
