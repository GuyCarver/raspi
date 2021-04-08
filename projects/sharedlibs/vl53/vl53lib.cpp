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
// FILE    vl53lib.cpp
// BY      gcarver
// DATE    04/08/2021 10:17 AM
//----------------------------------------------------------------------

//Module to handle communication with the VL53LOX time of flight sensor.
// This controller communicates using I2C.
// Much of this was pulled from Pololy library for arduino at:
// https://github.com/pololu/vl53l0X-arduino

//Compiled with g++ -Wall -pthread -o vl53lib vl53lib.cpp -lwiringpi -lrt

//NOTES:
// The address of a sensor reverts to default on disable or loss of power.
// It takes ~41ms to read the sensor.  This is too long to wait for so the
//  read should take place in a background thread.
// Separating the distance read into a trigger and read reduces the time to 5-7ms with
//  4-5ms taken in the trigger.  This is acceptable to me so I will not bother
//  putting the system into a background thread and instead use separated trigger/read calls.

// #define DEBUGOUT 1
#ifdef DEBUGOUT
#include <iostream>
#endif //DEBUGOUT

#include <unistd.h>								// for close()
#include <cstdint>
#include <wiringPiI2C.h>
#include <wiringPi.h>							// for delayMicroseconds()
#include <algorithm>							// for std::min/max

class vl53;

namespace
{
	enum PeriodType {
		PRE_RANGE,
		FINAL_RANGE
	};

	constexpr uint8_t _DEFAULT_ADDRESS = 0x29;
	constexpr uint8_t _SYSRANGE_START = 0x00;
	constexpr uint8_t _SYSTEM_THRESH_HIGH = 0x0C;
	constexpr uint8_t _SYSTEM_THRESH_LOW = 0x0E;
	constexpr uint8_t _SYSTEM_SEQUENCE_CONFIG = 0x01;
	constexpr uint8_t _SYSTEM_RANGE_CONFIG = 0x09;
	constexpr uint8_t _SYSTEM_INTERMEASUREMENT_PERIOD = 0x04;
	constexpr uint8_t _SYSTEM_INTERRUPT_CONFIG_GPIO = 0x0A;
	constexpr uint8_t _GPIO_HV_MUX_ACTIVE_HIGH = 0x84;
	constexpr uint8_t _SYSTEM_INTERRUPT_CLEAR = 0x0B;
	constexpr uint8_t _RESULT_INTERRUPT_STATUS = 0x13;
	constexpr uint8_t _RESULT_RANGE_STATUS = 0x14;
	constexpr uint8_t _ADDR_UNIT_ID_HIGH = 0x16;		// Serial number high byte
	constexpr uint8_t _ADDR_I2C_ID_HIGH = 0x18;			// Write serial number high byte for I2C address unlock
	constexpr uint8_t _RESULT_CORE_AMBIENT_WINDOW_EVENTS_RTN = 0xBC;
	constexpr uint8_t _RESULT_CORE_RANGING_TOTAL_EVENTS_RTN = 0xC0;
	constexpr uint8_t _RESULT_CORE_AMBIENT_WINDOW_EVENTS_REF = 0xD0;
	constexpr uint8_t _RESULT_CORE_RANGING_TOTAL_EVENTS_REF = 0xD4;
	constexpr uint8_t _RESULT_PEAK_SIGNAL_RATE_REF = 0xB6;
	constexpr uint8_t _ALGO_PART_TO_PART_RANGE_OFFSET_MM = 0x28;
	constexpr uint8_t _I2C_SLAVE_DEVICE_ADDRESS = 0x8A;
	constexpr uint8_t _MSRC_CONFIG_CONTROL = 0x60;
	constexpr uint8_t _PRE_RANGE_CONFIG_MIN_SNR = 0x27;
	constexpr uint8_t _PRE_RANGE_CONFIG_VALID_PHASE_LOW = 0x56;
	constexpr uint8_t _PRE_RANGE_CONFIG_VALID_PHASE_HIGH = 0x57;
	constexpr uint8_t _PRE_RANGE_MIN_COUNT_RATE_RTN_LIMIT = 0x64;
	constexpr uint8_t _FINAL_RANGE_CONFIG_MIN_SNR = 0x67;
	constexpr uint8_t _FINAL_RANGE_CONFIG_VALID_PHASE_LOW = 0x47;
	constexpr uint8_t _FINAL_RANGE_CONFIG_VALID_PHASE_HIGH = 0x48;
	constexpr uint8_t _FINAL_RANGE_CONFIG_MIN_COUNT_RATE_RTN_LIMIT = 0x44;
	constexpr uint8_t _PRE_RANGE_CONFIG_SIGMA_THRESH_HI = 0x61;
	constexpr uint8_t _PRE_RANGE_CONFIG_SIGMA_THRESH_LO = 0x62;
	constexpr uint8_t _PRE_RANGE_CONFIG_VCSEL_PERIOD = 0x50;
	constexpr uint8_t _PRE_RANGE_CONFIG_TIMEOUT_MACROP_HI = 0x51;
	constexpr uint8_t _PRE_RANGE_CONFIG_TIMEOUT_MACROP_LO = 0x52;
	constexpr uint8_t _SYSTEM_HISTOGRAM_BIN = 0x81;
	constexpr uint8_t _HISTOGRAM_CONFIG_INITIAL_PHASE_SELECT = 0x33;
	constexpr uint8_t _HISTOGRAM_CONFIG_READOUT_CTRL = 0x55;
	constexpr uint8_t _FINAL_RANGE_CONFIG_VCSEL_PERIOD = 0x70;
	constexpr uint8_t _FINAL_RANGE_CONFIG_TIMEOUT_MACROP_HI = 0x71;
	constexpr uint8_t _FINAL_RANGE_CONFIG_TIMEOUT_MACROP_LO = 0x72;
	constexpr uint8_t _CROSSTALK_COMPENSATION_PEAK_RATE_MCPS = 0x20;
	constexpr uint8_t _MSRC_CONFIG_TIMEOUT_MACROP = 0x46;
	constexpr uint8_t _SOFT_RESET_GO2_SOFT_RESET_N = 0xBF;
	constexpr uint8_t _IDENTIFICATION_MODEL_ID = 0xC0;
	constexpr uint8_t _IDENTIFICATION_REVISION_ID = 0xC2;
	constexpr uint8_t _OSC_CALIBRATE_VAL = 0xF8;
	constexpr uint8_t _GLOBAL_CONFIG_VCSEL_WIDTH = 0x32;
	constexpr uint8_t _GLOBAL_CONFIG_SPAD_ENABLES_REF_0 = 0xB0;
	constexpr uint8_t _GLOBAL_CONFIG_REF_EN_START_SELECT = 0xB6;
	constexpr uint8_t _DYNAMIC_SPAD_NUM_REQUESTED_REF_SPAD = 0x4E;
	constexpr uint8_t _DYNAMIC_SPAD_REF_EN_START_OFFSET = 0x4F;
	constexpr uint8_t _POWER_MANAGEMENT_GO1_POWER_FORCE = 0x80;
	constexpr uint8_t _VHV_CONFIG_PAD_SCL_SDA_EXTSUP_HV = 0x89;
	constexpr uint8_t _ADDR_I2C_SEC_ADDR = 0X8A;	// Write new I2C address after unlock
	constexpr uint8_t _INTERNAL_TUNING1 = 0x91;
	constexpr uint8_t _INTERNAL_TUNING2 = 0xFF;
	constexpr uint8_t _ALGO_PHASECAL_LIM = 0x30;
	constexpr uint8_t _ALGO_PHASECAL_CONFIG_TIMEOUT = 0x30;
	constexpr uint8_t _VCSEL_PERIOD_PRE_RANGE = 0;
	constexpr uint8_t _VCSEL_PERIOD_FINAL_RANGE = 1;

	template<typename T, uint32_t N> constexpr uint32_t arrlen(const T(&)[N]) { return N; }

	// Register init lists consist register/value pairs
	uint8_t I2CMode[] = {
		0x88,0x00,
		0x80,0x01,
		0xFF,0x01,
		0x00,0x00
	};

	uint8_t I2CMode2[] = {
		0x00,0x01,
		0xFF,0x00,
		0x80,0x00
	};

	uint8_t SPAD0[] = {
		0x80,0x01,
		0xFF,0x01,
		0x00,0x00,
		0xFF,0x06
	};

	uint8_t SPAD1[] = {
		0xFF,0x07,
		0x81,0x01,
		0x80,0x01,
		0x94,0x6B,
		0x83,0x00
	};

	uint8_t SPAD2[] = {
		0xFF,0x01,
		0x00,0x01,
		0xFF,0x00,
		0x80,0x00
	};

	uint8_t SPAD[] = {
		0xFF,0x01,
		0x4F,0x00,
		0x4E,0x2C,
		0xFF,0x00,
		0xB6,0xB4
	};

	uint8_t DefTuning[] = {
		0xFF,0x01, 0x00,0x00, 0xFF,0x00, 0x09,0x00,
		0x10,0x00, 0x11,0x00, 0x24,0x01, 0x25,0xFF,
		0x75,0x00, 0xFF,0x01, 0x4E,0x2C, 0x48,0x00,
		0x30,0x20, 0xFF,0x00, 0x30,0x09, 0x54,0x00,
		0x31,0x04, 0x32,0x03, 0x40,0x83, 0x46,0x25,
		0x60,0x00, 0x27,0x00, 0x50,0x06, 0x51,0x00,
		0x52,0x96, 0x56,0x08, 0x57,0x30, 0x61,0x00,
		0x62,0x00, 0x64,0x00, 0x65,0x00, 0x66,0xA0,
		0xFF,0x01, 0x22,0x32, 0x47,0x14, 0x49,0xFF,
		0x4A,0x00, 0xFF,0x00, 0x7A,0x0A, 0x7B,0x00,
		0x78,0x21, 0xFF,0x01, 0x23,0x34, 0x42,0x00,
		0x44,0xFF, 0x45,0x26, 0x46,0x05, 0x40,0x40,
		0x0E,0x06, 0x20,0x1A, 0x43,0x40, 0xFF,0x00,
		0x34,0x03, 0x35,0x44, 0xFF,0x01, 0x31,0x04,
		0x4B,0x09, 0x4C,0x05, 0x4D,0x04, 0xFF,0x00,
		0x44,0x00, 0x45,0x20, 0x47,0x08, 0x48,0x28,
		0x67,0x00, 0x70,0x04, 0x71,0x01, 0x72,0xFE,
		0x76,0x00, 0x77,0x00, 0xFF,0x01, 0x0D,0x01,
		0xFF,0x00, 0x80,0x01, 0x01,0xF8, 0xFF,0x01,
		0x8E,0x01, 0x00,0x01, 0xFF,0x00, 0x80,0x00
	};

	//----------------------------------------------------------------
	uint32_t CalcMacroPeriod( uint32_t aValue )
	{
		//(2304 * 1655 * period + 500) / 1000
		return (3813120u * aValue + 500u) / 1000u;
	}

	//----------------------------------------------------------------
	// Decode sequence step timeout in MCLKs from register value based on VL53L0X_decode_timeout()
	uint16_t DecodeTimeout( uint16_t aVal )
	{
		// format: "(LSByte * 2^MSByte) + 1"
		return ((aVal & 0xFF) << (aVal >> 8)) + 1;
	}

	//----------------------------------------------------------------
	// Encode sequence step timeout register value from timeout in MCLKs based on VL53L0X_encode_timeout()
	uint16_t EncodeTimeout( uint16_t aTimeout )
	{
		// format: "(LSByte * 2^MSByte) + 1"

		uint16_t msb = 0;

		if (aTimeout > 0) {

			uint16_t lsb = aTimeout - 1;

			while (lsb > 0xFF) {
				lsb >>= 1;
				++msb;
			}

			msb = (msb << 8) | (lsb & 0xFF);
		}
		return msb;
	}

	//----------------------------------------------------------------
	// Convert sequence step timeout from MCLKs to microseconds with given VCSEL period in PCLKs
	// based on VL53L0X_calc_timeout_us()
	uint32_t TimeoutMclks2US( uint16_t aTimeoutPeriodMclks, uint32_t aVcselPeriodPclks )
	{
		uint32_t periodNS = CalcMacroPeriod(aVcselPeriodPclks);
		return ((aTimeoutPeriodMclks * periodNS) + (periodNS / 2)) / 1000;
	}

	//----------------------------------------------------------------
	// Convert sequence step timeout from microseconds to MCLKs with given VCSEL period in PCLKs
	// based on VL53L0X_calc_aTimeout()
	uint32_t TimeoutUS2Mclks( uint32_t aTimeoutPeriodUS, uint32_t aVcselPeriodPclks )
	{
		uint32_t periodNS = CalcMacroPeriod(aVcselPeriodPclks);
		return (((aTimeoutPeriodUS * 1000) + (periodNS / 2)) / periodNS);
	}

	//----------------------------------------------------------------
	//Utility to read bits from the enables value.
	class Enables
	{
	public:
		Enables( ) = delete;
		explicit Enables( uint8_t aValue ) : _value(aValue) {  }

		bool TCC(  ) const { return (_value & 0x10) != 0;}
		bool DSS(  ) const { return (_value & 0x08) != 0;}
		bool MSRC(  ) const { return (_value & 0x04) != 0;}
		bool PreRange(  ) const { return (_value & 0x40) != 0;}
		bool FinalRange(  ) const { return (_value & 0x80) != 0;}
	private:
		uint8_t _value;
	};

	//----------------------------------------------------------------
	class SequenceStepTimeouts
	{
	public:
		uint16_t PreRangeVcselPeriodPclks = 0;
		uint16_t MSrcDssTccMclks = 0;
		uint16_t PreRangeMclks = 0;
		uint16_t FinalRangeMclks = 0;
		uint32_t MSrcDssTccUS = 0;
		uint32_t PreRangeUS = 0;
		uint32_t FinalRangeUS = 0;;
		uint8_t FinalRangeVcselPeriodPclks = 0;

		SequenceStepTimeouts( const vl53 &aVL, bool abPreRange );
	};
}	//namespace

//----------------------------------------------------------------
class vl53
{
public:
	//----------------------------------------------------------------
	//NOTE: For some reason long range true is actually shorter range even though
	// I've double checked the code and it seems correct.
	vl53( uint8_t aAddress = _DEFAULT_ADDRESS, bool abLongRange = false ) : _address(aAddress)
	{
		//If passed in address was 0 then set to default.
		if (_address == 0) {
			_address = _DEFAULT_ADDRESS;
		}

		// We first initialize using default address, if different address is requested
		//  we'll change it after initialization and setup a new connection.
		_i2c = wiringPiI2CSetup(_DEFAULT_ADDRESS);
		if (aAddress != _DEFAULT_ADDRESS) {
			ChangeAddress(aAddress);
			_i2c = wiringPiI2CSetup(aAddress);
		}
		Init(abLongRange);
	}

	//----------------------------------------------------------------
	~vl53(  )
	{
		close(_i2c);
	}

	//----------------------------------------------------------------
	//Trigger a Time of flight read.
	void TOFTrigger(  )
	{
// 		uint32_t timing = micros();

		//This is not an array because of the use of _stop.
		Write8(0x01, 0x80);
		Write8(0x01, 0xFF);
		Write8(0x00, 0x00);
		Write8(_stop, _INTERNAL_TUNING1);
		Write8(0x01, 0x00);
		Write8(0x00, 0xFF);
		Write8(0x80, 0x00);
		Write8(0x01, _SYSRANGE_START);

		// "Wait until start bit has been cleared"
		const uint32_t maxTimeout = 50;

		uint32_t timeout = 0;
		while (Read8(_SYSRANGE_START) & 0x01) {
			++timeout;
			delayMicroseconds(5000);
			if (timeout > maxTimeout) {
				return;
			}
		}

		_btriggered = true;

// 		timing = micros() - timing;
// 		std::cout << "DTrigger: " << timing << std::endl;
	}

	//----------------------------------------------------------------
	// Read the current distance in mm.  Note: the distance must have been triggered.
	int16_t TOFDistance(  )
	{
// 		uint32_t timing = micros();

		//If no distance read was triggered, simply return the old value.
		if (!_btriggered) {
			return _lastDistance;
		}

		_btriggered = false;					// Clear the flag.

		const uint32_t maxTimeout = 50;
		uint32_t timeout = 0;

		//Wait until interrupt occurs.
		while ((Read8(_RESULT_INTERRUPT_STATUS) & 0x07) == 0) {
			++timeout;
			delayMicroseconds(5000);
			if (timeout > maxTimeout) {
				return _lastDistance;
			}
		}

		_lastDistance = Read16(_RESULT_RANGE_STATUS + 10);
		Write8(0x01, _SYSTEM_INTERRUPT_CLEAR);

// 		timing = micros() - timing;
// 		std::cout << "DRead: " << timing << std::endl;

		return _lastDistance;
	}

	//----------------------------------------------------------------
	void GetModel( int32_t &arModel, int32_t &arRevision )
	{
		Write8(1, _IDENTIFICATION_MODEL_ID); // write address of register to read
		arModel = Read16(_IDENTIFICATION_MODEL_ID);

		Write8(1, _IDENTIFICATION_REVISION_ID);
		arRevision = Read8(_IDENTIFICATION_REVISION_ID);
	}

private:
	uint32_t _i2c;
	uint32_t _measurementTimingBudgetUS = 0;
	uint16_t _lastDistance = 0;					// Last read distance.
	uint8_t _stop = 0;							// Stop value written during Distance check.
	uint8_t _address;							// I2C address.
	bool _btriggered = false;					// Set to true when a new value read has been triggered.

	//----------------------------------------------------------------
	void Init( bool abLongRange )
	{
		Write8(Read8(_VHV_CONFIG_PAD_SCL_SDA_EXTSUP_HV) | 0x01, _VHV_CONFIG_PAD_SCL_SDA_EXTSUP_HV);

		WriteArray(I2CMode, arrlen(I2CMode));
		_stop = Read8(_INTERNAL_TUNING1);
		WriteArray(I2CMode2, arrlen(I2CMode2));

		//Disable SIGNAL_RATE_MSRC (bit 1) and SIGNAL_RATE_PRE_RANGE (bit 4)
		// limit checks
		auto config_control = Read8(_MSRC_CONFIG_CONTROL) | 0x12;
		Write8(config_control, _MSRC_CONFIG_CONTROL);
 		Write16(0x20, _FINAL_RANGE_CONFIG_MIN_COUNT_RATE_RTN_LIMIT);
		Write8(0xFF, _SYSTEM_SEQUENCE_CONFIG);

		bool spadTypeIsAperture = false;
		uint8_t spadCount = GetSPADInfo(spadTypeIsAperture);

		uint8_t refSpadA[6];
		ReadArray(refSpadA, arrlen(refSpadA), _GLOBAL_CONFIG_SPAD_ENABLES_REF_0);
		WriteArray(SPAD, arrlen(SPAD));

		uint8_t firstSPAD = spadTypeIsAperture ? 12 : 0;
		uint8_t spadsEnabled = 0;

		// clear bits for unused SPADs
		for (uint32_t i = 0; i < 48; ++i) {
			if ((i < firstSPAD) || (spadsEnabled == spadCount)) {
				refSpadA[i >> 3] &= ~(1 << (i & 7));
			}
			else if (refSpadA[i >> 3] & (1 << (i & 7))) {
				++spadsEnabled;
			}
		}

		WriteBuffer(refSpadA, arrlen(refSpadA), _GLOBAL_CONFIG_SPAD_ENABLES_REF_0);
		WriteArray(DefTuning, arrlen(DefTuning)); // long list of magic numbers

		// change some settings for long range mode
		if (abLongRange) {
			Write16(0x0D, _FINAL_RANGE_CONFIG_MIN_COUNT_RATE_RTN_LIMIT); // 0.1
			SetPulsePeriod(PeriodType::PRE_RANGE, 18);
			SetPulsePeriod(PeriodType::FINAL_RANGE, 14);
		}

		// set interrupt configuration to "new sample ready"
		Write8(0x04, _SYSTEM_INTERRUPT_CONFIG_GPIO);
		delayMicroseconds(50);
		Write8(Read8(_GPIO_HV_MUX_ACTIVE_HIGH) & ~0x10, _GPIO_HV_MUX_ACTIVE_HIGH); // active low
		Write8(0x01, _SYSTEM_INTERRUPT_CLEAR);

		ReadMeasurementTimingBudget();
		Write8(0xE8, _SYSTEM_SEQUENCE_CONFIG);
		SetMeasurementTimingBudget(_measurementTimingBudgetUS);
		Write8(0x01, _SYSTEM_SEQUENCE_CONFIG);

		if (SingleRefCalibration(0x40)) {
			Write8(0x02, _SYSTEM_SEQUENCE_CONFIG);
			// Restore the previous Sequence Config
			if (SingleRefCalibration(0x00)) {
				Write8(0xE8, _SYSTEM_SEQUENCE_CONFIG);
			}
		}
	}

	//----------------------------------------------------------------
	uint8_t GetSPADInfo( bool &arTypeIsAperture )
	{
		int32_t timeout = 0;
		const int32_t maxTimeout = 50;

		WriteArray(SPAD0, arrlen(SPAD0));
		Write8(Read8(0x83) | 0x04, 0x83);
		WriteArray(SPAD1, arrlen(SPAD1));

		while (timeout < maxTimeout) {
			if (Read8(0x83) != 0x00) {
				break;
			}
			++timeout;
			delayMicroseconds(5000);
		}

		if (timeout >= maxTimeout) {
#ifdef DEBUGOUT
			std::cout << "timout getting spad info.\n";
#endif //DEBUGOUT
			return 0;
		}

		Write8(0x01, 0x83);
		uint8_t temp = Read8(0x92);
		arTypeIsAperture = (temp & 0x80) != 0;
		Write8(0x00, 0x81);
		Write8(0x06, _INTERNAL_TUNING2);
		Write8(Read8(0x83) & ~0x04, 0x83);
		WriteArray(SPAD2, arrlen(SPAD2));

		return temp & 0x7F;
	}

	//----------------------------------------------------------------
	// Set the VCSEL (vertical cavity surface emitting laser) pulse period for the
	// given period type (pre-range or final range) to the given value in PCLKs.
	// Longer periods seem to increase the potential range of the sensor.
	// Valid values are (even numbers only):
	//  pre:  12 to 18 (initialized default: 14)
	//  final: 8 to 14 (initialized default: 10)
	// based on VL53L0X_set_vcsel_pulse_period()
	void SetPulsePeriod( PeriodType aType, uint8_t aPeriod )
	{
		Enables en(Read8(_SYSTEM_SEQUENCE_CONFIG));

		SequenceStepTimeouts timeouts(*this, en.PreRange());

		// "Apply specific settings for the requested clock period"
		// "Re-calculate and apply timeouts, in macro periods"

		// "When the VCSEL period for the pre or final range is changed,
		// the corresponding timeout must be read from the device using
		// the current VCSEL period, then the new VCSEL period can be
		// applied. The timeout then must be written back to the device
		// using the new VCSEL period.
		//
		// For the MSRC timeout, the same applies - this timeout being
		// dependant on the pre-range vcsel period."
		uint16_t v = 0;

		if (aType == PeriodType::PRE_RANGE) {
			// "Set phase check limits"
			switch (aPeriod) {
				case 12:
					v = 0x1808;
				break;
				case 14:
					v = 0x3008;
				break;
				case 16:
					v = 0x4008;
				break;
				case 18:
					v = 0x5008;
				break;
				default:
					aPeriod = 12;
					v = 0x1808;
				break;
			}
			Write16(v, _PRE_RANGE_CONFIG_VALID_PHASE_LOW);

			// apply new VCSEL period
			Write8((aPeriod >> 1) - 1, _PRE_RANGE_CONFIG_VCSEL_PERIOD);

			// update timeouts

			uint16_t new_pre_range_aTimeout = TimeoutUS2Mclks(timeouts.PreRangeUS, aPeriod);

			Write16(EncodeTimeout(new_pre_range_aTimeout), _PRE_RANGE_CONFIG_TIMEOUT_MACROP_HI);

			uint16_t new_msrc_aTimeout = TimeoutUS2Mclks(timeouts.MSrcDssTccUS, aPeriod);

			Write8(static_cast<uint8_t>(std::min(new_msrc_aTimeout - 1, 255)), _MSRC_CONFIG_TIMEOUT_MACROP);
		}
		else {		// FINAL_RANGE.
			uint16_t v0;
			uint8_t v1, v2, v3;
			switch (aPeriod) {
				case 8:
					v0 = 0x1008;
					v1 = 0x02;
					v2 = 0x0C;
					v3 = 0x30;
				break;
				case 10:
					v0 = 0x2808;
					v1 = 0x03;
					v2 = 0x09;
					v3 = 0x20;
				break;
				case 12:
					v0 = 0x3808;
					v1 = 0x03;
					v2 = 0x08;
					v3 = 0x20;
				break;
				case 14:
					v0 = 0x4808;
					v1 = 0x03;
					v2 = 0x07;
					v3 = 0x20;
				break;
				default:
					v0 = 0x1008;
					v1 = 0x02;
					v2 = 0x0C;
					v3 = 0x30;
				break;
			}
			Write16(v0, _FINAL_RANGE_CONFIG_VALID_PHASE_HIGH);
			Write8(v1, _GLOBAL_CONFIG_VCSEL_WIDTH);
			Write8(v2, _ALGO_PHASECAL_CONFIG_TIMEOUT);
			Write8(0x01, _INTERNAL_TUNING2);
			Write8(v3, _ALGO_PHASECAL_LIM);
			Write8(0x00, _INTERNAL_TUNING2);

			// apply new VCSEL period
			Write8((aPeriod >> 1) - 1, _FINAL_RANGE_CONFIG_VCSEL_PERIOD);

			// update timeouts

			// "For the final range timeout, the pre-range timeout
			//  must be added. To do this both final and pre-range
			//  timeouts must be expressed in macro periods MClks
			//  because they have different vcsel periods."

			uint16_t new_finalRangeTimeout = TimeoutUS2Mclks(timeouts.FinalRangeUS, aPeriod);

			if (en.PreRange()) {
				new_finalRangeTimeout += timeouts.PreRangeMclks;
			}

			Write16(EncodeTimeout(new_finalRangeTimeout), _FINAL_RANGE_CONFIG_TIMEOUT_MACROP_HI);
		}

		// "Finally, the timing budget must be re-applied"

		SetMeasurementTimingBudget(_measurementTimingBudgetUS);

		// "Perform the phase calibration. This is needed after changing on vcsel period."

		uint8_t sequence_config = Read8(_SYSTEM_SEQUENCE_CONFIG);
		Write8(0x02, _SYSTEM_SEQUENCE_CONFIG);
		SingleRefCalibration(0x0);
		Write8(sequence_config, _SYSTEM_SEQUENCE_CONFIG);
	}


	//----------------------------------------------------------------
	// Set the measurement timing budget in microseconds, which is the time allowed
	// for one measurement; the ST API and this library take care of splitting the
	// timing budget among the sub-steps in the ranging sequence. A longer timing
	// budget allows for more accurate measurements. Increasing the budget by a
	// factor of N decreases the range measurement standard deviation by a factor of
	// sqrt(N). Defaults to about 33 milliseconds; the minimum is 20 ms.
	// based on VL53L0X_set_measurement_timing_budget_micro_seconds()
	void SetMeasurementTimingBudget( uint32_t aBudget )
	{
		const uint32_t MinTimingBudget		= 20000;
		if (aBudget < MinTimingBudget) {
			return;
		}

		const uint16_t StartOverhead		= 1320; // note that this is different than the value in get_
		const uint16_t EndOverhead			= 960;
		const uint16_t MsrcOverhead			= 660;
		const uint16_t TccOverhead			= 590;
		const uint16_t DssOverhead			= 690;
		const uint16_t PreRangeOverhead		= 660;
		const uint16_t FinalRangeOverhead	= 550;

		uint32_t usedBudgetUS = StartOverhead + EndOverhead;

		Enables en(Read8(_SYSTEM_SEQUENCE_CONFIG));

		SequenceStepTimeouts timeouts(*this, en.PreRange());

		if (en.TCC()) {
			usedBudgetUS += timeouts.MSrcDssTccUS + TccOverhead;
		}

		if (en.DSS()) {
			usedBudgetUS += 2 * (timeouts.MSrcDssTccUS + DssOverhead);
		}
		else if (en.MSRC()) {
			usedBudgetUS += timeouts.MSrcDssTccUS + MsrcOverhead;
		}
		if (en.PreRange()) {
			usedBudgetUS += timeouts.PreRangeUS + PreRangeOverhead;
		}
		if (en.FinalRange()) {
			usedBudgetUS += FinalRangeOverhead;

			// "Note that the final range timeout is determined by the timing
			// budget and the sum of all other timeouts within the sequence.
			// If there is no room for the final range timeout, then an error
			// will be set. Otherwise the remaining time will be applied to
			// the final range."

			//If budget in range, then set it.
			if (usedBudgetUS <= aBudget) {
				// "Requested timeout too big."

				uint32_t finalRangeTimeoutUS = aBudget - usedBudgetUS;

				// "For the final range timeout, the pre-range timeout
				//  must be added. To do this both final and pre-range
				//  timeouts must be expressed in macro periods MClks
				//  because they have different vcsel periods."

				uint16_t finalRangeTimeout = TimeoutUS2Mclks(finalRangeTimeoutUS, timeouts.FinalRangeVcselPeriodPclks);

				if (en.PreRange()) {
					finalRangeTimeout += timeouts.PreRangeMclks;
				}
				Write16(EncodeTimeout(finalRangeTimeout), _FINAL_RANGE_CONFIG_TIMEOUT_MACROP_HI);
			}
		}
	}

	//----------------------------------------------------------------
	void ReadMeasurementTimingBudget(  )
	{
		uint16_t const StartOverhead = 1910; // note that this is different than the value in set_
		uint16_t const EndOverhead = 960;
		uint16_t const TccOverhead = 590;
		uint16_t const DssOverhead  = 690;
		uint16_t const MsrcOverhead = 660;
		uint16_t const PreRangeOverhead = 660;
		uint16_t const FinalRangeOverhead = 550;

		uint16_t budget_us = StartOverhead + EndOverhead;

		Enables en(Read8(_SYSTEM_SEQUENCE_CONFIG));

		SequenceStepTimeouts timeouts(*this, en.PreRange());

		if (en.TCC()) {
			budget_us += timeouts.MSrcDssTccUS + TccOverhead;
		}

		if (en.DSS()) {
			budget_us += 2 * (timeouts.MSrcDssTccUS + DssOverhead);
		}
		else if (en.MSRC()) {
			budget_us += timeouts.MSrcDssTccUS + MsrcOverhead;
		}

		if (en.PreRange()) {
			budget_us += timeouts.PreRangeUS + PreRangeOverhead;
		}

		if (en.FinalRange()) {
			budget_us += timeouts.FinalRangeUS + FinalRangeOverhead;
		}

		_measurementTimingBudgetUS = budget_us;
	}

	//----------------------------------------------------------------
	bool SingleRefCalibration( uint8_t aVhvInitByte )
	{
		Write8(0x01 | aVhvInitByte, _SYSRANGE_START);	// VL53L0X_REG_SYSRANGE_MODE_START_STOP

		uint32_t timeout = 0;
		const uint32_t maxTimeout = 100;
		while ((Read8(_RESULT_INTERRUPT_STATUS) & 0x07) == 0) {
			if (++timeout > maxTimeout) {
				return false;					// Exit with error.
			}
			delayMicroseconds(5000);
		}

#ifdef DEBUGOUT
		if (timeout > maxTimeout) {
			std::cout << "timeout reading single ref calibration.\n";
		}
#endif //DEBUGOUT

		Write8(0x01, _SYSTEM_INTERRUPT_CLEAR);
		Write8(0x00, _SYSRANGE_START);

		return true;
	}

public:

	//----------------------------------------------------------------
	// Read 8 bit value and return.
	const uint8_t Read8( uint32_t aLoc ) const
	{
		uint8_t v = 0;
		int32_t ret = wiringPiI2CReadReg8(_i2c, aLoc);
		//If the value is <0 it's a read error.
		if (ret >= 0) {
			v = static_cast<uint8_t>(ret);
		}
		return v;
	}

	//----------------------------------------------------------------
	// Read 16 bit value and return.
	const uint16_t Read16( uint32_t aLoc ) const
	{
		uint16_t v = 0;
		int32_t ret = wiringPiI2CReadReg16(_i2c, aLoc);
		//If the value is <0 it's a read error.
		if (ret >= 0) {
			v = static_cast<uint16_t>(ret);
			v = (v >> 8) | (v << 8);			// Endian swap.
		}
		return v;
	}

	//----------------------------------------------------------------
	// Read array of 8 bit values into buffer.
	void ReadArray( uint8_t *apBuffer, uint32_t aLen, uint8_t aLoc ) const
	{
		for ( uint32_t i = 0; i < aLen; ++i) {
			apBuffer[i] = Read8(aLoc + i);
		}
	}

	//----------------------------------------------------------------
	// Write 8 bit integer aVal to given address aLoc.
	int32_t Write8( uint8_t aValue, uint32_t aLoc ) const
	{
		return wiringPiI2CWriteReg8(_i2c, aLoc, aValue);
	}

	//----------------------------------------------------------------
	// Write 16 bit integer aVal to given address aLoc.
	int32_t Write16( uint16_t aValue, uint32_t aLoc ) const
	{
		aValue = (aValue >> 8) | (aValue << 8);	// Endian Swap.
		return wiringPiI2CWriteReg16(_i2c, aLoc, aValue);
	}

	//----------------------------------------------------------------
	// Iterate array of loc/value pairs.
	void WriteArray( uint8_t *apBuffer, uint32_t aLen ) const
	{
		for ( uint32_t i = 0; i < aLen; i += 2) {
			Write8(apBuffer[i + 1], apBuffer[i]);
		}
	}

	//----------------------------------------------------------------
	// Write 8 bit buffer to given address.
	void WriteBuffer( uint8_t *apBuffer, uint32_t aLen, uint32_t aLoc ) const
	{
		for ( uint32_t i = 0; i < aLen; ++i) {
			Write8(apBuffer[i], aLoc + i);
		}
	}

	//----------------------------------------------------------------
	// Address change lasts only per session and is
	void ChangeAddress( uint8_t aAddress )
	{
		//Read then write ID to unlock address change.
		uint16_t adr = Read16(_ADDR_UNIT_ID_HIGH);
		Write16(adr, _ADDR_I2C_ID_HIGH);
		//Write the new address.
		Write8(aAddress, _ADDR_I2C_SEC_ADDR);
	}
};

/*
//----------------------------------------------------------------
int32_t main( int32_t aArgs, char *aArgv[] )
{
	wiringPiSetupGpio();
	pinMode(4, OUTPUT);
	digitalWrite(4, 1);

	auto v = vl53(0x30);
	int32_t model, revision;
	v.GetModel(model, revision);
	std::cout << "model: " << model << " revision: " << revision << std::endl;

	while (true) {
		v.TOFTrigger();							// Trigger a distance read.
		delayMicroseconds(500000);
		auto dist = v.TOFRead();				// Read the value from the trigger.
		std::cout << "distance: " << dist << std::endl; // "        \r";
	}

	return 0;
}
*/

namespace
{

//----------------------------------------------------------------
SequenceStepTimeouts::SequenceStepTimeouts( const vl53 &aVL, bool abPreRange )
{
	PreRangeVcselPeriodPclks = ((aVL.Read8(_PRE_RANGE_CONFIG_VCSEL_PERIOD) + 1) & 0xFF) << 1;
	MSrcDssTccMclks = aVL.Read8(_MSRC_CONFIG_TIMEOUT_MACROP) + 1;
	MSrcDssTccUS = TimeoutMclks2US(MSrcDssTccMclks, PreRangeVcselPeriodPclks);

	PreRangeMclks = DecodeTimeout(aVL.Read8(_PRE_RANGE_CONFIG_TIMEOUT_MACROP_HI));

	PreRangeUS = TimeoutMclks2US(PreRangeMclks, PreRangeVcselPeriodPclks);
	FinalRangeVcselPeriodPclks = ((aVL.Read8(_FINAL_RANGE_CONFIG_VCSEL_PERIOD) + 1) & 0xFF) << 1;
	FinalRangeMclks = DecodeTimeout(aVL.Read16(_FINAL_RANGE_CONFIG_TIMEOUT_MACROP_HI));

	if (abPreRange) {
		FinalRangeMclks -= PreRangeMclks;
	}

	FinalRangeUS = TimeoutMclks2US(FinalRangeMclks, FinalRangeVcselPeriodPclks);
}

} //namespace

//Following are the external interface functions.
extern "C"
{

//--------------------------------------------------------
void *Create( uint8_t aAddress, bool abLongRange )
{
	return new vl53(aAddress, abLongRange);
}

//--------------------------------------------------------
void Release( void *apInstance )
{
	auto pinstance = reinterpret_cast<vl53*>(apInstance);
	delete pinstance;
}

//--------------------------------------------------------
void Update( void *apInstance )
{
	auto pinstance = reinterpret_cast<vl53*>(apInstance);
	pinstance->TOFTrigger();
}

//--------------------------------------------------------
uint16_t Distance( void *apInstance )
{
	auto pinstance = reinterpret_cast<vl53*>(apInstance);
	return pinstance->TOFDistance();
}

} //extern "C"
