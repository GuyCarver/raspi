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
// FILE    pca9865.cpp
// BY      gcarver
// DATE    08/14/2020 10:25 PM
//----------------------------------------------------------------------

//Module to handle communication with the PCA9865 16 servo controller
// This controller communicates using I2C.

#include <iostream>
#include <unistd.h>
#include <errno.h>
#include <wiringPiI2C.h>
#include <wiringPi.h>

namespace
{
	constexpr uint32_t _ADDRESS = 0x40;
	constexpr uint32_t _MODE1 = 0x0;
	constexpr uint32_t _PRESCALE = 0xFE;
	constexpr uint32_t _LED0_ON_L = 0x6;		// We only use LED0 and offset 0-16 from it.
// 	constexpr uint32_t _LED0_ON_H = 0x7;
// 	constexpr uint32_t _LED0_OFF_L = 0x8;
// 	constexpr uint32_t _LED0_OFF_H = 0x9;
// 	constexpr uint32_t _ALLLED_ON_L = 0xFA;
// 	constexpr uint32_t _ALLLED_ON_H = 0xFB;
// 	constexpr uint32_t _ALLLED_OFF_L = 0xFC;
// 	constexpr uint32_t _ALLLED_OFF_H = 0xFD;

	constexpr uint32_t _DEFAULTFREQ = 100;
	//The min/max were determined using trial and error with a frequency of 100.
	constexpr uint32_t _MINPULSE = 260; //120;
	constexpr uint32_t _MAXPULSE = 1080; //868;
	constexpr uint32_t _RANGE = _MAXPULSE - _MINPULSE;
	constexpr uint32_t _END = 4095; // - _RANGE;
}	//namespace

//--------------------------------------------------------
class pca9865
{
public:

	//--------------------------------------------------------
	pca9865( uint32_t aFreq = _DEFAULTFREQ )
	{
		_i2c = wiringPiI2CSetup(_ADDRESS);		// If this is -1 an error occurred.
		delayMicroseconds(50);					// Wait for init to settle.
		auto res = _write8(0, _MODE1);
		bGood = res >= 0;

		setfreq(aFreq);
		alloff();								// Make sure we don't move to 0 or things jerk.

		_instance = this;						// We only have 1 instance of this object.
	}

	//--------------------------------------------------------
	~pca9865(  )
	{
		close(_i2c);
		_instance = nullptr;
	}

	//--------------------------------------------------------
	// Set frequency for all servos.  A good value is 60hz (default).
	void setfreq( float aFreq )
	{
		aFreq *= 0.9999f;						// Correct for overshoot in frequency setting.
		if (aFreq < 1.0f) { aFreq = 1.0f; } else if (aFreq > 3500.0f) { aFreq = 3500.0f; }
		float prescalefloat = (6103.51562f / aFreq) - 1.0f;  // 25000000 / 4096 / freq.
		auto prescale = static_cast<uint8_t>(prescalefloat + 0.5f);

		uint8_t oldmode = _read(_MODE1);
		uint8_t newmode = (oldmode & 0x7F) | 0x10;
		_write8(newmode, _MODE1);
		_write8(prescale, _PRESCALE);
		_write8(oldmode, _MODE1);
		delayMicroseconds(50);
		_write8(oldmode | 0xA1, _MODE1);			// This sets the MODE1 register to turn on auto increment.
	}

	//--------------------------------------------------------
	// Turn off a servo.
	void off( uint32_t aServo )
	{
		_setpwm(aServo, 0, 0);
	}

	//--------------------------------------------------------
	// Turn all servos off.
	void alloff(  )
	{
		for ( uint32_t i = 0; i < 16; ++i) {
			off(i);
		}
	}

	//--------------------------------------------------------
	// Set the 0.0-1.0. If < 0 turns servo off.
	void set( uint32_t aServo, float aPerc )
	{
		if (aPerc < 0.0f) {
			off(aServo);
		}
		else {
			uint32_t base = _MINPULSE + (_RANGE * aServo);
			while (base > _END) {
				base -= _END;
			}

			int32_t val = base + static_cast<int32_t>((_RANGE * aPerc));
			while (val > _END) {
				val -= _END;
			}
// 			std::cout << "Vals: " << base << val << std::endl;
			_setpwm(aServo, base, val);
		}
	}

	//--------------------------------------------------------
	// Set angle -90 to +90.  < -90 is off.
	void setangle( uint32_t aServo, float aAngle )
	{
		// (a + 90.0) / 180.0
		float perc = (aAngle + 90.0f) * 0.005556f;  //Convert angle +/- 90 to 0.0-1.0
		set(aServo, perc);
	}

	void setpwm( uint32_t aServo, uint32_t aOn, uint32_t aOff )
	{
		_setpwm(aServo, aOn, aOff);
	}

	//--------------------------------------------------------
	static pca9865 *QInstance(  ) { return _instance; }

	//--------------------------------------------------------
	bool QGood( ) const { return bGood; }

private:
	int32_t _i2c = 0;
	bool bGood = true;

	static pca9865 *_instance;

	//--------------------------------------------------------
	// Read 8 bit value and return.
	const uint8_t _read( uint32_t aLoc )
	{
		uint8_t v = 0;
		int32_t ret = wiringPiI2CReadReg8(_i2c, aLoc);
		//If the value is <0 it's a read error.
		if (ret >= 0) {
			v = static_cast<uint8_t>(ret);
		}
		return v;
	}

	//--------------------------------------------------------
	// Write 8 bit integer aVal to given address aLoc.
	int32_t _write8( uint8_t aValue, uint32_t aLoc )
	{
		return wiringPiI2CWriteReg8(_i2c, aLoc, aValue);
	}

	//--------------------------------------------------------
	// Write 8 bit buffer to given address.
	void _writebuffer( uint8_t *apBuffer, uint32_t aLen, uint32_t aLoc )
	{
		for ( uint32_t i = 0; i < aLen; ++i) {
			_write8(apBuffer[i], aLoc + i);
		}
	}

	//--------------------------------------------------------
	// aServo = 0-15.
	// aOn = 16 bit on value.
	// aOff = 16 bit off value.
	void _setpwm( uint32_t aServo, uint32_t aOn, uint32_t aOff )
	{
		if ((0 <= aServo) && (aServo <= 15)) {
			uint8_t buffer[4];
			// Data = on-low, on-high, off-low and off-high.  That's 4 bytes each servo.
			uint32_t loc = _LED0_ON_L + (aServo * 4);
			buffer[0] = static_cast<uint8_t>(aOn & 0xFF);
			buffer[1] = static_cast<uint8_t>(aOn >> 8);
			buffer[2] = static_cast<uint8_t>(aOff & 0xFF);
			buffer[3] = static_cast<uint8_t>(aOff >> 8);
			_writebuffer(buffer, 4, loc);
		}
	}
};

pca9865 *pca9865::_instance = nullptr;

//Following are the external interface functions.
extern "C"
{

//--------------------------------------------------------
bool Startup(  )
{
	if (!pca9865::QInstance()) {
		auto p = new pca9865();
	}
	return pca9865::QInstance()->QGood();
}

//--------------------------------------------------------
bool IsGood(  )
{
	auto p = pca9865::QInstance();
	return p ? p->QGood() : false;
}

//--------------------------------------------------------
void Shutdown(  )
{
	auto p = pca9865::QInstance();
	if (p) {
		delete p;
	}
}

//--------------------------------------------------------
void SetFreq( float aFreq )
{
	auto p = pca9865::QInstance();
	if (p) {
		p->setfreq(aFreq);
	}
}

//--------------------------------------------------------
void Off( uint32_t aServo )
{
	auto p = pca9865::QInstance();
	if (p) {
		p->off(aServo);
	}
}

//--------------------------------------------------------
void AllOff(  )
{
	auto p = pca9865::QInstance();
	if (p) {
		p->alloff();
	}
}

//--------------------------------------------------------
// Set servo to percentage (0.0-1.0)
void Set( uint32_t aServo, float aPerc )
{
	auto p = pca9865::QInstance();
	if (p) {
		p->set(aServo, aPerc);
	}
}

//--------------------------------------------------------
// Set angle to range -90/+90
void SetAngle( uint32_t aServo, float aAngle )
{
	auto p = pca9865::QInstance();
	if (p) {
		p->setangle(aServo, aAngle);
	}
}

void SetPWM( uint32_t aServo, uint32_t aOn, uint32_t aOff )
{
	auto p = pca9865::QInstance();
	if (p) {
		p->setpwm(aServo, aOn, aOff);
	}
}

} //extern C
