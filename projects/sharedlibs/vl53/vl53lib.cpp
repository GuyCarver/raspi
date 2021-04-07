//----------------------------------------------------------------------
// FILE    vl53.cpp
// BY      gcarver
// DATE    08/15/2020 11:26 PM
//----------------------------------------------------------------------

//Module to handle communication with the VL53LOX time of flight sensor.
// This controller communicates using I2C.
// Much of this was pulled from Pololy library for arduino at:
// https://github.com/pololu/vl53l0X-arduino

//Compiled with g++ -Wall -pthread -o vl53lib vl53lib.cpp -lwiringpi -lrt

#define DEBUGOUT 1
#ifdef DEBUGOUT
#include <iostream>
#endif //DEBUGOUT

#include <unistd.h>								// for close()
#include <cstdint>
#include <wiringPiI2C.h>
#include <wiringPi.h>							// for delayMicroseconds()
#include <algorithm>							// for std::min/max

namespace
{
	const uint8_t SEQUENCE_ENABLE_FINAL_RNG		= 0x80;
	const uint8_t SEQUENCE_ENABLE_PRE_RNG		= 0x40;
	const uint8_t SEQUENCE_ENABLE_TCC			= 0x10;
	const uint8_t SEQUENCE_ENABLE_DSS			= 0x08;
	const uint8_t SEQUENCE_ENABLE_MSRC			= 0x04;

	enum PeriodType {
		PRE_RANGE,
		FINAL_RANGE
	};

//Registers, only the ones that are used. Others are at:
// https://github.com/GrimbiXcode/VL53L0X-Register-Map
// Don't bother checking the data sheet.  Not in there.
	enum REGS : uint8_t {
		SYSRANGE_START					= 0x00,
		SYSTEM_SEQUENCE_CFG				= 0x01,
		SYSTEM_INTERRUPT_CFG_GPIO		= 0x0A,
		SYSTEM_INTERRUPT_CLEAR			= 0x0B,
		RESULT_INTERRUPT_STATUS			= 0x13,
		RESULT_RNG_STATUS				= 0x14,
		ADDR_UNIT_ID_HIGH				= 0x16, // Serial number high byte
		ADDR_I2C_ID_HIGH				= 0x18, // Write serial number high byte for I2C address unlock
		ALGO_PHASECAL_LIM				= 0x30,
		ALGO_PHASECAL_CFG_TIMEOUT		= 0x30,
		GLOBAL_CFG_VCSEL_WIDTH			= 0x32,
		FINAL_RNG_CFG_MIN_COUNT_RATE_RTN_LIMIT = 0x44,
		MSRC_CFG_TIMEOUT_MACROP			= 0x46,
		FINAL_RNG_CFG_VALID_PHASE_HIGH	= 0x48,
		PRE_RNG_CFG_VCSEL_PERIOD		= 0x50,
		PRE_RNG_CFG_TIMEOUT_MACROP_HI	= 0x51,
		PRE_RNG_CFG_VALID_PHASE_LOW		= 0x56,
		REG_MSRC_CFG_CONTROL			= 0x60,
		FINAL_RNG_CFG_VCSEL_PERIOD		= 0x70,
		FINAL_RNG_CFG_TIMEOUT_MACROP_HI	= 0x71,
		GPIO_HV_MUX_ACTIVE_HIGH			= 0x84,
		VHV_CFG_PAD_SCL_SDA_EXTSUP_HV	= 0x89,
		ADDR_I2C_SEC_ADDR				= 0X8A,	// Write new I2C address after unlock
		INTERNAL_TUNING1				= 0x91,
		GLOBAL_CFG_SPAD_ENABLES_REF_0	= 0xB0,
		REG_IDENTIFICATION_MODEL_ID		= 0xC0,
		REG_IDENTIFICATION_REVISION_ID	= 0xC2,
		INTERNAL_TUNING2				= 0xFF,
	};

	template<typename T, uint32_t N>
	constexpr uint32_t arrlen(const T(&)[N])
	{
		return N / 2;
	}

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
	uint32_t TimeoutMclks2US( uint16_t aTimeoutPeriodMclks, uint8_t aVcselPeriodPclks )
	{
		uint32_t periodNS = CalcMacroPeriod(aVcselPeriodPclks);
		return ((aTimeoutPeriodMclks * periodNS) + (periodNS / 2)) / 1000;
	}

	//----------------------------------------------------------------
	// Convert sequence step timeout from microseconds to MCLKs with given VCSEL period in PCLKs
	// based on VL53L0X_calc_aTimeout()
	uint32_t TimeoutUS2Mclks( uint32_t aTimeoutPeriodUS, uint8_t aVcselPeriodPclks )
	{
		uint32_t periodNS = CalcMacroPeriod(aVcselPeriodPclks);
		return (((aTimeoutPeriodUS * 1000) + (periodNS / 2)) / periodNS);
	}

}	//namespace

class vl53;

//----------------------------------------------------------------
class SequenceStepTimeouts
{
public:
	uint16_t PreRangeVcselPeriodPclks = 0;
	uint16_t FinalRangeVcselPeriodPclks = 0;
	uint16_t MSrcDssTccMclks = 0;
	uint16_t PreRangeMclks = 0;
	uint16_t FinalRangeMclks = 0;
	uint32_t MSrcDssTccUS = 0;
	uint32_t PreRangeUS = 0;
	uint32_t FinalRangeUS = 0;;

	SequenceStepTimeouts( const vl53 &aVL, uint8_t aEnables );
};

//----------------------------------------------------------------
class vl53
{
public:
	//----------------------------------------------------------------
	vl53( uint32_t aAddress, bool abLongRange ) : _address(aAddress)
	{
		// Add to instance array.
		_i2c = wiringPiI2CSetup(aAddress);
		Init(abLongRange);
	}

	//----------------------------------------------------------------
	~vl53(  )
	{
		close(_i2c);
	}

	//----------------------------------------------------------------
	int32_t ReadRangeContinuousMM(  )
	{
		uint32_t timeout = 0;
		uint16_t range;

		while ((Read8(RESULT_INTERRUPT_STATUS) & 0x07) == 0) {
			++timeout;
			delayMicroseconds(5000);
			if (timeout > 50) {
				return -1;
			}
		}

		// assumptions: Linearity Corrective Gain is 1000 (default);
		// fractional ranging is not enabled
		range = Read16(RESULT_RNG_STATUS + 10);
		Write8(0x01, SYSTEM_INTERRUPT_CLEAR);
		return range;
	}

	//----------------------------------------------------------------
	// Read the current distance in mm
	int32_t TOFReadDistance(  )
	{
		Write8(0x01, 0x80);
		Write8(0x01, 0xFF);
		Write8(0x00, 0x00);
		Write8(_stop, INTERNAL_TUNING1);
		Write8(0x01, 0x00);
		Write8(0x00, 0xFF);
		Write8(0x80, 0x00);

		Write8(0x01, SYSRANGE_START);

		// "Wait until start bit has been cleared"
		uint32_t timeout = 0;
		while (Read8(SYSRANGE_START) & 0x01) {
			++timeout;
			delayMicroseconds(5000);
			if (timeout > 50u) {
				return -1;
			}
		}

		return ReadRangeContinuousMM();
	}

	//----------------------------------------------------------------
	void GetModel( int32_t &arModel, int32_t &arRevision )
	{
		Write8(1, REG_IDENTIFICATION_MODEL_ID); // write address of register to read
		arModel = Read8(REG_IDENTIFICATION_MODEL_ID);

		Write8(1, REG_IDENTIFICATION_REVISION_ID);
		arRevision = Read8(REG_IDENTIFICATION_REVISION_ID);
	}

	//----------------------------------------------------------------
	// Address change lasts only per session and is
	void ChangeAddress( uint8_t aAddress )
	{
		if (aAddress == _address) {
			return;
		}

		//Read then write ID to unlock address change.
		uint16_t adr = Read16(ADDR_UNIT_ID_HIGH);
		Write16(adr, ADDR_I2C_ID_HIGH);
		//Write the new address.
		Write8(aAddress, ADDR_I2C_SEC_ADDR);
		_address = aAddress;
	}

private:
	uint32_t _i2c = 0;
	uint32_t MeasurementTimingBudgetUS = 0;
	uint8_t _address = 0x29;
	uint8_t _stop = 0;

	friend class SequenceStepTimeouts;

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
	// Write 16 bit buffer to given address.
	void WriteBuffer( uint16_t *apBuffer, uint32_t aLen, uint32_t aLoc ) const
	{
		for ( uint32_t i = 0; i < aLen; ++i) {
			Write16(apBuffer[i], aLoc + i);
		}
	}

	//----------------------------------------------------------------
	void Init( bool abLongRange )
	{
		uint8_t spadCount = 0;
		uint8_t spadTypeIsAperture = 0;
		uint8_t refSpadA[6];
		uint8_t firstSPAD, spadsEnabled;

		// set 2.8V mode by setting bit 0 of this register.
		Write8(Read8(VHV_CFG_PAD_SCL_SDA_EXTSUP_HV) | 0x01, VHV_CFG_PAD_SCL_SDA_EXTSUP_HV);
		// Set I2C standard mode
		WriteArray(I2CMode, arrlen(I2CMode));
		_stop = Read8(INTERNAL_TUNING1);
		WriteArray(I2CMode2, arrlen(I2CMode2));
		// disable SIGNAL_RATE_MSRC (bit 1) and SIGNAL_RATE_PRE_RANGE (bit 4) limit checks
		Write8(Read8(REG_MSRC_CFG_CONTROL) | 0x12, REG_MSRC_CFG_CONTROL);
		// Fixed point format of 9 integer bits and 7 fraction bits
		Write16(0x20, FINAL_RNG_CFG_MIN_COUNT_RATE_RTN_LIMIT);
		Write8(0xFF, SYSTEM_SEQUENCE_CFG);
		GetSPADInfo(&spadCount, &spadTypeIsAperture);

		ReadArray(refSpadA, arrlen(refSpadA), GLOBAL_CFG_SPAD_ENABLES_REF_0);
		WriteArray(SPAD, arrlen(SPAD));
		firstSPAD = spadTypeIsAperture ? 12 : 0;
		spadsEnabled = 0;

		// clear bits for unused SPADs
		for (uint32_t i = 0; i < 48; ++i) {
			if ((i < firstSPAD) || (spadsEnabled == spadCount)) {
				refSpadA[i >> 3] &= ~(1 << (i & 7));
			}
			else if (refSpadA[i >> 3] & (1 << (i & 7))) {
				++spadsEnabled;
			}
		}

		WriteBuffer(refSpadA, arrlen(refSpadA), GLOBAL_CFG_SPAD_ENABLES_REF_0);
		WriteArray(DefTuning, arrlen(DefTuning)); // long list of magic numbers

		// change some settings for long range mode
		if (abLongRange) {
			Write16(0x0D, FINAL_RNG_CFG_MIN_COUNT_RATE_RTN_LIMIT); // 0.1
			SetPulsePeriod(PeriodType::PRE_RANGE, 18);
			SetPulsePeriod(PeriodType::FINAL_RANGE, 14);
		}

		// set interrupt configuration to "new sample ready"
		Write8(0x04, SYSTEM_INTERRUPT_CFG_GPIO);
		Write8(Read8(GPIO_HV_MUX_ACTIVE_HIGH) & ~0x10, GPIO_HV_MUX_ACTIVE_HIGH); // active low
		Write8(0x01, SYSTEM_INTERRUPT_CLEAR);
		MeasurementTimingBudgetUS = GetMeasurementTimingBudget();
		Write8(0xE8, SYSTEM_SEQUENCE_CFG);
		SetMeasurementTimingBudget(MeasurementTimingBudgetUS);
		Write8(0x01, SYSTEM_SEQUENCE_CFG);
		if (SingleRefCalibration(0x40)) {
			Write8(0x02, SYSTEM_SEQUENCE_CFG);
			if (SingleRefCalibration(0x00)) {
				Write8(0xE8, SYSTEM_SEQUENCE_CFG);
			}
		}
	}

	//----------------------------------------------------------------
	void GetSPADInfo( uint8_t *apCount, uint8_t *apTypeIsAperture )
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
			return;
		}
		Write8(0x01, 0x83);
		uint8_t temp = Read8(0x92);
		*apCount = temp & 0x7F;
		*apTypeIsAperture = temp & 0x80;
		Write8(0x00, 0x81);
		Write8(0x06, INTERNAL_TUNING2);
		Write8(Read8(0x83) & ~0x04, 0x83);
		WriteArray(SPAD2, arrlen(SPAD2));
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
		uint8_t enables = Read8(SYSTEM_SEQUENCE_CFG);

		SequenceStepTimeouts timeouts(*this, enables);

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
			Write16(v, PRE_RNG_CFG_VALID_PHASE_LOW);

			// apply new VCSEL period
			Write8((aPeriod >> 1) - 1, PRE_RNG_CFG_VCSEL_PERIOD);

			// update timeouts

			uint16_t new_pre_range_aTimeout =
				TimeoutUS2Mclks(timeouts.PreRangeUS, aPeriod);

			Write16(EncodeTimeout(new_pre_range_aTimeout),
				PRE_RNG_CFG_TIMEOUT_MACROP_HI);

			uint16_t new_msrc_aTimeout =
				TimeoutUS2Mclks(timeouts.MSrcDssTccUS, aPeriod);

			Write8(static_cast<uint8_t>(std::min(new_msrc_aTimeout - 1, 255)),
				MSRC_CFG_TIMEOUT_MACROP);
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
			Write16(v0, FINAL_RNG_CFG_VALID_PHASE_HIGH);
			Write8(v1, GLOBAL_CFG_VCSEL_WIDTH);
			Write8(v2, ALGO_PHASECAL_CFG_TIMEOUT);
			Write8(0x01, INTERNAL_TUNING2);
			Write8(v3, ALGO_PHASECAL_LIM);
			Write8(0x00, INTERNAL_TUNING2);

			// apply new VCSEL period
			Write8((aPeriod >> 1) - 1, FINAL_RNG_CFG_VCSEL_PERIOD);

			// update timeouts

			// "For the final range timeout, the pre-range timeout
			//  must be added. To do this both final and pre-range
			//  timeouts must be expressed in macro periods MClks
			//  because they have different vcsel periods."

			uint16_t new_finalRangeTimeout =
				TimeoutUS2Mclks(timeouts.FinalRangeUS, aPeriod);

			if (enables & SEQUENCE_ENABLE_PRE_RNG) {
				new_finalRangeTimeout += timeouts.PreRangeMclks;
			}

			Write16(EncodeTimeout(new_finalRangeTimeout),
			FINAL_RNG_CFG_TIMEOUT_MACROP_HI);
		}

		// "Finally, the timing budget must be re-applied"

		SetMeasurementTimingBudget(MeasurementTimingBudgetUS);

		// "Perform the phase calibration. This is needed after changing on vcsel period."

		uint8_t sequence_config = Read8(SYSTEM_SEQUENCE_CFG);
		Write8(0x02, SYSTEM_SEQUENCE_CFG);
		SingleRefCalibration(0x0);
		Write8(sequence_config, SYSTEM_SEQUENCE_CFG);
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

		uint8_t enables = Read8(SYSTEM_SEQUENCE_CFG);
		SequenceStepTimeouts timeouts(*this, enables);

		if (enables & SEQUENCE_ENABLE_TCC)	{
			usedBudgetUS += timeouts.MSrcDssTccUS + TccOverhead;
		}

		if (enables & SEQUENCE_ENABLE_DSS) {
			usedBudgetUS += 2 * (timeouts.MSrcDssTccUS + DssOverhead);
		}
		else if (enables & SEQUENCE_ENABLE_MSRC) {
			usedBudgetUS += timeouts.MSrcDssTccUS + MsrcOverhead;
		}
		if (enables & SEQUENCE_ENABLE_PRE_RNG) {
			usedBudgetUS += timeouts.PreRangeUS + PreRangeOverhead;
		}
		if (enables & SEQUENCE_ENABLE_FINAL_RNG) {
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

				uint16_t finalRangeTimeout =
					TimeoutUS2Mclks(finalRangeTimeoutUS, timeouts.FinalRangeVcselPeriodPclks);

				if (enables & SEQUENCE_ENABLE_PRE_RNG) {
					finalRangeTimeout += timeouts.PreRangeMclks;
				}
				Write16(EncodeTimeout(finalRangeTimeout), FINAL_RNG_CFG_TIMEOUT_MACROP_HI);

				MeasurementTimingBudgetUS = aBudget; // store for internal reuse
			}
		}
	}

	//----------------------------------------------------------------
	uint32_t GetMeasurementTimingBudget(  )
	{
		uint16_t const StartOverhead = 1910; // note that this is different than the value in set_
		uint16_t const EndOverhead = 960;
		uint16_t const MsrcOverhead = 660;
		uint16_t const TccOverhead = 590;
		uint16_t const DssOverhead  = 690;
		uint16_t const PreRangeOverhead = 660;
		uint16_t const FinalRangeOverhead = 550;

		// "Start and end overhead times always present"
		uint32_t budgetUS = StartOverhead + EndOverhead;

		uint8_t enables = Read8(SYSTEM_SEQUENCE_CFG);
		SequenceStepTimeouts timeouts(*this, enables);

		if (enables & SEQUENCE_ENABLE_TCC) {
			budgetUS += (timeouts.MSrcDssTccUS + TccOverhead);
		}

		if (enables & SEQUENCE_ENABLE_DSS) {
			budgetUS += 2 * (timeouts.MSrcDssTccUS + DssOverhead);
		}
		else if (enables & SEQUENCE_ENABLE_MSRC) {
			budgetUS += (timeouts.MSrcDssTccUS + MsrcOverhead);
		}

		if (enables & SEQUENCE_ENABLE_PRE_RNG) {
			budgetUS += (timeouts.PreRangeUS + PreRangeOverhead);
		}

		if (enables & SEQUENCE_ENABLE_FINAL_RNG) {
			budgetUS += (timeouts.FinalRangeUS + FinalRangeOverhead);
		}

		MeasurementTimingBudgetUS = budgetUS; // store for internal reuse
		return budgetUS;
	}

	//----------------------------------------------------------------
	bool SingleRefCalibration( uint8_t aVhvInitByte )
	{
		Write8(0x01 | aVhvInitByte, SYSRANGE_START);	// VL53L0X_REG_SYSRANGE_MODE_START_STOP

		uint32_t timeout = 0;
		while ((Read8(RESULT_INTERRUPT_STATUS) & 0x07) == 0) {
			timeout++;
			delayMicroseconds(5000);
			if (timeout > 100) { return false; }
		}

		Write8(0x01, SYSTEM_INTERRUPT_CLEAR);
		Write8(0x00, SYSRANGE_START);

		return true;
	}

};

//----------------------------------------------------------------
int32_t main( int32_t aArgs, char *aArgv[] )
{
	auto v = vl53(0x29, true);
	int32_t model, revision;
	v.GetModel(model, revision);
	std::cout << "model: " << model << " revision: " << revision << std::endl;

	while (true) {
		auto dist = v.TOFReadDistance();
		std::cout << "distance: " << dist << "        \r";
		delayMicroseconds(50000);
	}

	return 0;
}

//----------------------------------------------------------------
SequenceStepTimeouts::SequenceStepTimeouts( const vl53 &aVL, uint8_t aEnables )
{
	PreRangeVcselPeriodPclks = ((aVL.Read8(PRE_RNG_CFG_VCSEL_PERIOD) + 1) << 1);
	MSrcDssTccMclks = aVL.Read8(MSRC_CFG_TIMEOUT_MACROP) + 1;
	MSrcDssTccUS = TimeoutMclks2US(MSrcDssTccMclks, PreRangeVcselPeriodPclks);
	PreRangeMclks = DecodeTimeout(aVL.Read8(PRE_RNG_CFG_TIMEOUT_MACROP_HI));
	PreRangeUS = TimeoutMclks2US(PreRangeMclks, PreRangeVcselPeriodPclks);
	FinalRangeVcselPeriodPclks = ((aVL.Read8(FINAL_RNG_CFG_VCSEL_PERIOD) + 1) << 1);
	FinalRangeMclks = DecodeTimeout(aVL.Read16(FINAL_RNG_CFG_TIMEOUT_MACROP_HI));

	if (aEnables & SEQUENCE_ENABLE_PRE_RNG) {
		FinalRangeMclks -= PreRangeMclks;
	}

	FinalRangeUS = TimeoutMclks2US(FinalRangeMclks, FinalRangeVcselPeriodPclks);
}

//Following are the external interface functions.
extern "C"
{

//--------------------------------------------------------
void *Create( uint32_t aAddress, uint32_t aType )
{
	return new vl53(aAddress, aType);
}

//--------------------------------------------------------
void Release( void *apInstance )
{
	auto pinstance = reinterpret_cast<vl53*>(apInstance);
	delete pinstance;
}

//--------------------------------------------------------
void SetAddress( void *apInstance, uint32_t aAddress )
{
	auto pinstance = reinterpret_cast<vl53*>(apInstance);
	pinstance->ChangeAddress(static_cast<uint8_t>(aAddress));
}

//--------------------------------------------------------
uint32_t GetData( void *apInstance )
{
	auto pinstance = reinterpret_cast<vl53*>(apInstance);
	return pinstance->TOFReadDistance();
}

} //extern "C"
