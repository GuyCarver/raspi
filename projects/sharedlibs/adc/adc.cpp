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
// FILE    adc.cpp
// DATE    04/21/2021 09:13 PM
//----------------------------------------------------------------------

//Module to handle communication with the ads1115 Analog to Digital converter.
// This controller communicates using I2C.

#include <iostream>
#include <unistd.h>
#include <cstdint>
#include <sys/ioctl.h>							// To set ioctl method on the open file
#include <linux/i2c-dev.h>						// For ISC_SLAVE
#include <wiringPiI2C.h>
#include <wiringPi.h>

namespace
{
	constexpr uint8_t _ADDRESS = 0x48;			// Default (GND)
												//0x49 = VCC, 0x4A = SDA, 0x4B = SDL

	constexpr uint8_t _RA_CONVERSION = 0x00;
	constexpr uint8_t _RA_CONFIG = 0x01;

	constexpr uint16_t _OS_SINGLE = 0x8000;		// Write: Set to start a single-conversion
	constexpr uint16_t _OS_NOTBUSY = 0x8000;	// Bit set to 1 on _RA_CONFIG read when no conversion in progress

	constexpr uint16_t _MUX_MASK = 0x7000;

	constexpr uint16_t _CQUE_NONE = 0x03;

	constexpr uint16_t _CLAT_NONLATCHING = 0x00;
	constexpr uint16_t _CLAT_LATCHING = 0x01;

	constexpr uint16_t _CPOL_ACTIVELOW = 0x00;
	constexpr uint16_t _CPOL_ACTIVEHIGH = 0x01;

	constexpr uint16_t _MODE_CONTINUOUS = 0x0000;
	constexpr uint16_t _MODE_SINGLESHOT = 0x0100;


	//--------------------------------------------------------
	enum class MUX : uint16_t
	{
		_MUX_DIFF_0_1,		// 0x0 Differential P  =  AIN0, N  =  AIN1 (default)
		_MUX_DIFF_0_3,		// 0x1 Differential P  =  AIN0, N  =  AIN3
		_MUX_DIFF_1_3,		// 0x2 Differential P  =  AIN1, N  =  AIN3
		_MUX_DIFF_2_3,		// 0x3 Differential P  =  AIN2, N  =  AIN3
		_MUX_SINGLE_0,		// 0x4 Single-ended AIN0
		_MUX_SINGLE_1,		// 0x5 Single-ended AIN1
		_MUX_SINGLE_2,		// 0x6 Single-ended AIN2
		_MUX_SINGLE_3		// 0x7 Single-ended AIN3
	};

	constexpr uint16_t _RATEPOS = 5;
	constexpr uint16_t _GAINPOS = 9;
	constexpr uint16_t _MUXPOS = 12;
	constexpr uint16_t _RATEMASK = 0x7 << _RATEPOS;
	constexpr uint16_t _GAINMASK = 0x7 << _GAINPOS;

	//--------------------------------------------------------
	uint16_t min( uint16_t aV1, uint16_t aV2 )
	{
		return aV1 < aV2 ? aV1 : aV2;
	}

}	//namespace

//--------------------------------------------------------
class adc
{
public:
	//--------------------------------------------------------
	adc( uint8_t aAddress = _ADDRESS, uint16_t aRate = 4, uint16_t aGain = 2 )
	: _address(aAddress)
	{
		_i2c = wiringPiI2CSetup(_address);

		SetRate(aRate);
		SetGain(aGain);
	}

	//--------------------------------------------------------
	~adc(  )
	{
		close(_i2c);
	}

	//--------------------------------------------------------
	void SetRate( uint16_t aRate )
	{
		_mode = (_mode & ~_RATEMASK) | (min(7u, aRate) << _RATEPOS);
	}

	//--------------------------------------------------------
	void SetGain( uint16_t aGain )
	{
		_mode = (_mode & ~_GAINMASK) | (min(5u, aGain) << _GAINPOS);
	}

	//--------------------------------------------------------
	uint16_t Read( MUX aMux )
	{
		_write16(_mode | (static_cast<uint16_t>(aMux) << _MUXPOS), _RA_CONFIG);
		//NOTE: Try _read8 and _OS_NOTBUSY >> 8.
		//When bit is set the conversion is inactive.
		while ((_read16(_RA_CONFIG) & _OS_NOTBUSY) == 0) {
			delayMicroseconds(1);
		}
		return _read16(_RA_CONVERSION);
	}

private:
	uint32_t _i2c = 0;
	uint16_t _mode = _CQUE_NONE | _MODE_SINGLESHOT | _OS_SINGLE;
	uint8_t _address;

	//--------------------------------------------------------
	uint8_t _read8( uint8_t aLoc )
	{
		return wiringPiI2CReadReg8(_i2c, aLoc);
	}

	//--------------------------------------------------------
	uint16_t _read16( uint8_t aLoc )
	{
		uint8_t vh = wiringPiI2CReadReg8(_i2c, aLoc);
		uint8_t vl = wiringPiI2CReadReg8(_i2c, aLoc + 1);
		return (vh << 8) | (vl & 0xFF);
	}

	//--------------------------------------------------------
	// Write 16 bit integer aVal to given address aLoc.
	void _write16( uint16_t aValue, uint8_t aLoc, uint32_t aDelay = 5 )
	{
		uint8_t data[4];
		i2c_smbus_ioctl_data args;

		args.read_write = 0;
		args.command = aLoc;
		args.size = 8u;
		args.data = reinterpret_cast<i2c_smbus_data*>(data);
		data[0] = 2;
		data[1] = static_cast<uint8_t>(aValue >> 8);
		data[2] = static_cast<uint8_t>(aValue);
		auto res = ioctl(_i2c, I2C_SMBUS, &args);

		if (res < 0) {
			std::cout << "adc write16 error." << std::endl;
		}

// 		wiringPiI2CWriteReg8(_i2c, aLoc, aValue >> 8);
// 		wiringPiI2CWriteReg8(_i2c, aLoc + 1, aValue);
		if (aDelay) {
			delayMicroseconds(aDelay);
		}
	}
};

extern "C"
{

//--------------------------------------------------------
void *Create( uint8_t aAddress = _ADDRESS )
{
	return new adc(aAddress);
}

//--------------------------------------------------------
void Release( void *apInstance )
{
	auto padc = reinterpret_cast<adc*>(apInstance);
	delete padc;
}

//--------------------------------------------------------
uint16_t Read( void *apInstance, uint16_t aMux )
{
	auto padc = reinterpret_cast<adc*>(apInstance);
	return padc->Read(static_cast<MUX>(aMux & 7));
}
} //extern C

//--------------------------------------------------------
int32_t main(  )
{
	auto a= Create();
	while (true) {
		uint16_t v = Read(a, static_cast<uint16_t>(MUX::_MUX_SINGLE_0));
		std::cout << "Data: " << v << "      \r";
		delayMicroseconds(10000);
	}
	return 0;
}
