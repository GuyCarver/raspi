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
// FILE    hcsr04lib.cpp
// BY      gcarver
// DATE    04/05/2021 09:41 AM
//----------------------------------------------------------------------

#include <cstdint>
#include <wiringPi.h>

// #define DEBUGOUT 1
#ifdef DEBUGOUT
#include <iostream>
#endif //DEBUGOUT

//--------------------------------------------------------
// Reads the distance from the echo pin, however it waits in a tight loop.
//  This causes a pause in the rest of the system.  Need to use a background thread
//  to read the data using an interrupt.
class hcsr04
{
public:

	//--------------------------------------------------------
	hcsr04( uint32_t aTrigger, uint32_t aEcho )
	: Trigger(aTrigger)
	, Echo(aEcho)
	, b3Pin(aEcho == aTrigger)
	{
		pinMode(Echo, INPUT);
		pullUpDnControl(Echo, PUD_DOWN);
		pinMode(Trigger, OUTPUT);
		digitalWrite(Trigger, LOW);
	}

	//--------------------------------------------------------
	uint32_t Update(  )
	{
		//Trigger the signal.
		digitalWrite(Trigger, HIGH);
		delayMicroseconds(10);
		digitalWrite(Trigger, LOW);

		//If in 3 pin mode we have to set the pin mode to input.
		if (b3Pin) {
			pinMode(Echo, INPUT);
		}

		//Now wait for the return.
		auto start = micros();
		int32_t res;

		//Wait for the pin to go high to indicate distance sensing has started.
		do
		{
			res = digitalRead(Echo);
		} while(res == LOW);

		//Now wait for timout or for pin to go low to get distance.
		for ( uint32_t count = 0; (res == HIGH) && (count < 50000); ++count) {
			res = digitalRead(Echo);
		}
		auto end = micros();

		//If in 3 pin mode, set the pin back to output.
		if (b3Pin) {
			pinMode(Trigger, OUTPUT);
		}

		auto dt = end - start;

		//If msb is set, the counter wrapped around so subtract from 0 to get the right value.
		// Can't just negate dt because it's an unsigned value.
		if (dt & 0x80000000) {
			dt = 0 - dt;
		}

#ifdef DEBUGOUT
		std::cout << "Time: " << dt << std::endl;
#endif //DEBUGOUT

		return dt;
	}

	//--------------------------------------------------------
	static void Startup(  )
	{
		if (!bInitialized) {
			bInitialized = true;
			wiringPiSetupGpio();
		}
	}

private:
	uint32_t Trigger;
	uint32_t Echo;
	bool b3Pin;									// Indicate if in 3 pin mode.
	static bool bInitialized;					// Indicates if wiringPi has been initialized.
};

bool hcsr04::bInitialized = false;

//Following are the external interface functions.
extern "C"
{

//--------------------------------------------------------
void *Create( uint32_t aTrigger, uint32_t aEcho )
{
	hcsr04::Startup();
	return new hcsr04(aTrigger, aEcho);
}

//--------------------------------------------------------
void Release( void *apInstance )
{
	auto phcsr = reinterpret_cast<hcsr04*>(apInstance);
	delete phcsr;
}

//--------------------------------------------------------
uint32_t Update( void *apInstance )
{
	auto phcsr = reinterpret_cast<hcsr04*>(apInstance);
	return phcsr->Update();
}

} //extern "C"
