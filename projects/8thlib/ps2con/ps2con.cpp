//----------------------------------------------------------------------
// Copyright (c) 2018, gcarver
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
// FILE    ps2con.cpp
// BY      Guy Carver
// DATE    04/30/2018 12:36 PM
//----------------------------------------------------------------------

#include <memory>
#include <iostream>
#include <string>
#include <stdio.h>
#include <wiringPi.h>

static const unsigned char cmd_qmode[] = {1,0x41,0,0,0};			//Add the below bytes in to qdata to read analog (analog button mode needs to be set)
static const unsigned char cmd_qdata[] = {1,0x42,0,0,0,0,0,0,0};	//,0,0,0,0,0,0,0,0,0,0,0,0,0)
static const unsigned char cmd_enter_config[] = {1,0x43,0,1,0};
static const unsigned char cmd_exit_config[] = {1,0x43,0,0,0x5A,0x5A,0x5A,0x5A,0x5A};
static const unsigned char cmd_set_mode[] = {1,0x44,0,1,3,0,0,0,0};	//1 = analog stick mode, 3 = lock mode button. Don't remember which byte to set though.

//Button values. Bit 1 = changed, Bit 0 = Down state.
enum VALUES {
	UP,
	DOWN,										// Button is down.
	RELEASED,									// Indiciates button was just released.
	PRESSED										// Indicate button was just pressed.
};

//_buttons array indexes
enum BUTTONS {
	SELECT,
	L_HAT,
	R_HAT,
	START,
	DPAD_U,
	DPAD_R,
	DPAD_D,
	DPAD_L,
	L_TRIGGER,
	R_TRIGGER,
	L_SHOULDER,
	R_SHOULDER,
	TRIANGLE,
	CIRCLE,
	CROSS,
	SQUARE,
	COUNT
};

//_joys array indexes.
enum JOYS {
	RX = 0x10,									// This is just after BUTTONS::SQUARE.
	RY,
	LX,
	LY,
	JOYCOUNT
};

//----------------------------------------------------------------
const char *Names[] = {
	"SELECT",
	"L_HAT",
	"R_HAT",
	"START",
	"DPAD_U",
	"DPAD_R",
	"DPAD_D",
	"DPAD_L",
	"L_TRIGGER",
	"R_TRIGGER",
	"L_SHOULDER",
	"R_SHOULDER",
	"TRIANGLE",
	"CIRCLE",
	"CROSS",
	"SQUARE",
	"LX",
	"LY",
	"RX",
	"RY"
};

class ps2con;

///
/// ps2 controller driver object.
///
class ps2con
{
public:

	//----------------------------------------------------------------
	ps2con( uint32_t aCmd, uint32_t aData, uint32_t aClk, uint32_t aAtt )
	: _cmd(aCmd)
	, _data(aData)
	, _clk(aClk)
	, _att(aAtt)
	{
		//Read data, but probably not necessary, maybe just the delay is, but without these
		// initialization may not succeed.
		pinMode(_cmd, OUTPUT);
//		pullUpDnControl(_cmd, PUD_DOWN);
		pinMode(_data, INPUT);
		pinMode(_clk, OUTPUT);
//		pullUpDnControl(_clk, PUD_DOWN);
		pinMode(_att, OUTPUT);
//		pullUpDnControl(_att, PUD_DOWN);

		GetData();
		DelayUS(100);
		GetData();
		DelayUS(100);

		DoConfig();
		DelayUS(3);

		//Read data a few times to settle out state changes.  Don't know why more than
		// a couple are needed but 6 is the minimum to be safe.
		for ( uint32_t i = 0; i < 6; ++i) {
			GetData();
			DelayUS(100);
		}
	}

	//----------------------------------------------------------------
	// Send configuration data to controller.
	void DoConfig(  )
	{
		SendReceive(cmd_enter_config, sizeof(cmd_enter_config));

		DelayUS(3);
		SendReceive(cmd_set_mode, sizeof(cmd_set_mode));
		DelayUS(3);
	//Put these in to enable rumble and variable pressure buttons.
	//	SendReceive(cmd_enable_rumble, sizeof(cmd_enable_rumble));
	//	DelayUS(3);
	//	SendReceive(cmd_enable_analog, sizeof(cmd_enable_analog));
	//	DelayUS(3);
		SendReceive(cmd_exit_config, sizeof(cmd_exit_config));
	}

	//----------------------------------------------------------------
	static void DelayUS( uint32_t us )
	{
		delayMicroseconds(us);
	}

	//----------------------------------------------------------------
	static void SetPin( uint32_t aPin, bool aValue )
	{
		digitalWrite(aPin, aValue ? HIGH : LOW);
	}

	//----------------------------------------------------------------
	static bool GetPin( uint32_t aPin )
	{
		auto v = digitalRead(aPin);
		return (v != 0);
	}

	//----------------------------------------------------------------
	//Send given data and receive into _res array.
	void SendReceive( const uint8_t *apData, uint32_t aLen )
	{
		SetPin(_att, false);					// Set self->_att to 0 to tell controller we are going to send.
		DelayUS(1);

		//Loop through all of the characters and send them.
		for ( uint32_t i = 0; i < aLen; ++i) {
			uint8_t value = 0;
			uint8_t snd = apData[i];

			for ( uint32_t j = 0; j < 8; ++j) {
				//Set self->_cmd to high if snd & 1
				SetPin(_cmd, (snd & 1) != 0);
				snd >>= 1;
				SetPin(_clk, false);			// Set _clk low.
				DelayUS(8);						// Delay must be at least 5 to work.
				value |= GetPin(_data) << j;
				SetPin(_clk, true);				// set _clk high.
				DelayUS(8);						// Delay must be at least 5 to work.
			}
			_res[i] = value;					// Store the read value into result buffer.
		}
		SetPin(_att, true);						// Set self->_att to 1.
		DelayUS(3);								// Delay just in case.
	}

	//----------------------------------------------------------------
	//Read data and process into _buttons and _joys arrays.
	void GetData(  )
	{
		SendReceive(cmd_qdata, sizeof(cmd_qdata));

		//Double buffer button input so we can check for state changes.
		uint32_t prev = _prevbuttons;
		uint32_t b = _res[3] | (_res[4] << 8);
		_prevbuttons = b;						// Set new prev buttons for next time.
		for ( uint32_t i = 0; i < BUTTONS::COUNT; ++i) {
			uint8_t bv = !(b & 1);
			//If == then value changed because the prev check doesn't negate the bit like bv setting above.
			if (bv == (prev & 1)) {
				bv |= RELEASED;					// Bit 1 set = changed state.  Bit 0 = up/down state.
			}
			_buttons[i] = bv;

			b >>= 1;
			prev >>= 1;
		}

		int32_t sgn = 1;
		//Loop through joystick input and change values 0-255 to +/- 255 with 0 in the middle.
		for ( uint32_t i = 5; i < 9; ++i) {
			_joys[i - 5] = ((_res[i] - 0x80) << 1) * sgn;
			sgn = -sgn;							// Every other input (y) needs to be reversed.
		}
	}

	uint32_t _cmd = 0;
	uint32_t _data = 0;
	uint32_t _clk = 0;
	uint32_t _att = 0;

	uint32_t _prevbuttons = 0;
	int32_t _joys[4];
	uint8_t _buttons[BUTTONS::COUNT];
	uint8_t _res[sizeof(cmd_qdata)];
};

namespace
{
bool bInitialized = false;
std::unique_ptr<ps2con> pInstance = nullptr;
}	//namespace

//Following are the functions 8th will be using.

extern "C" {

//----------------------------------------------------------------
//Initialize the gpio system and create our singleton instance of ps2con.
bool Startup( uint32_t aCmd, uint32_t aData, uint32_t aClk, uint32_t aAtt )
{
	if (!bInitialized) {
		wiringPiSetupGpio();
		bInitialized = true;
	}

	pInstance = std::make_unique<ps2con>(aCmd, aData, aClk, aAtt);

	return true; 							// TODO: Determine is ps2con connection is good.
}

//----------------------------------------------------------------
//Kill our ps2con instance.
void Shutdown(  )
{
	pInstance = nullptr;
}

//----------------------------------------------------------------
//Read new data from the controller.
void Update(  )
{
	if (pInstance) {
		pInstance->GetData();
	}
}

//----------------------------------------------------------------
//Rerun the configuration process on the controller.
void Config(  )
{
	if (pInstance) {
		pInstance->DoConfig();
	}
}

//----------------------------------------------------------------
//Get button value given an index.
uint32_t GetButton( uint32_t aIndex )
{
	return pInstance && aIndex < BUTTONS::COUNT
	? pInstance->_buttons[aIndex]
	: 0u;
}

//----------------------------------------------------------------
//Get joystick value given an index.
int32_t GetJoy( uint32_t aIndex )
{
	//If the input values are _LX etc, they have an additional bit set to start them at index 16.  Strip that off
	// so the index starts at 0.
	return pInstance ? pInstance->_joys[aIndex & 0x03] : 0;
}

//----------------------------------------------------------------
//Get button or joystick name for the given index.
const char *GetName( uint32_t aIndex )
{
	return aIndex < JOYS::JOYCOUNT
	? Names[aIndex]
	: "";
}

//----------------------------------------------------------------
//Get a string representation of the ps2con raw data.
const char *GetString(  )
{
	if (pInstance) {
		static char mystring[256];
		sprintf(mystring, "ps2con._data = %X,%X,%X,%X,%X,%X,%X,%X,%X",
			pInstance->_res[0],
			pInstance->_res[1],
			pInstance->_res[2],
			pInstance->_res[3],
			pInstance->_res[4],
			pInstance->_res[5],
			pInstance->_res[6],
			pInstance->_res[7],
			pInstance->_res[8]
			);
		return mystring;
	}
	else {
		return "No ps2con Instance.";
	}
}

}  //extern c

