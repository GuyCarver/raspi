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

#include <cstdlib>
#include <cstdint>
#include <wiringPi.h>

//#define DEBUGOUT 1
#ifdef DEBUGOUT
#include <iostream>
#endif //DEBUGOUT

//NOTE: Interrupt doesn't work with 3 pin mode. Switching the pin to output
// messes up the interrupt system.  I attempted to reset it but that had no affect.

//The winringPi interrupt callback system doesn't have a payload, so we have
// to supply a unique function for each pin. This is the signature of the
// interrupt callback function.
typedef void (*cbFunction)(  );

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

		InterruptA[aEcho] = this;

		pinMode(Trigger, OUTPUT);
		digitalWrite(Trigger, LOW);

		//Set the ISR function to trigger on FALLING (Pin goes to 0).
		wiringPiISR(aEcho, INT_EDGE_FALLING, callbacks[aEcho]);
	}

	//--------------------------------------------------------
	void Update(  )
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
		Start = micros();
		bWaiting = true;						// Set waiting for interupt.
	}

	//--------------------------------------------------------
	//Callback to read the time at falling edge of pin change.
	void SetTime(  )
	{
		if (bWaiting) {
			bWaiting = false;

			uint32_t dt = micros() - Start;

			//If msb is set, the counter wrapped around so subtract from 0 to get the right value.
			// Can't just negate dt because it's an unsigned value.
			if (dt & 0x80000000) {
				dt = 0 - dt;
			}

			//If in 3 pin mode, set the pin back to output.
			if (b3Pin) {
				pinMode(Trigger, OUTPUT);
			}

			Time = dt;
		}
	}

	//--------------------------------------------------------
	static void Startup(  )
	{
		if (!bInitialized) {
			bInitialized = true;
			wiringPiSetupGpio();
		}
	}

	uint32_t QTime(  ) const { return Time; }

private:
	uint32_t Trigger;
	uint32_t Echo;
	uint32_t Time = 0;
	uint32_t Start = 0;
	bool b3Pin;									// Indicate if in 3 pin mode.
	bool bWaiting = false;						// When True, waiting for interrupt.
	static bool bInitialized;					// Indicates if wiringPi has been initialized.
	static hcsr04 *InterruptA[32];				// Array of hcsr04 objects by pin.
	static cbFunction callbacks[];				// Array of unique interrupt callback functions.

	//--------------------------------------------------------
	template<uint32_t P> static void callback(  )
	{
#ifdef DEBUGOUT
		std::cout << "callback" << P << std::endl;
#endif //DEBUGOUT
		hcsr04 *phc  = InterruptA[P];
		if (phc) {
			phc->SetTime();
		}
	}

};

bool hcsr04::bInitialized = false;
hcsr04 *hcsr04::InterruptA[] = { nullptr };

//--------------------------------------------------------
cbFunction hcsr04::callbacks[] = {
	hcsr04::callback<0>,
	hcsr04::callback<1>,
	hcsr04::callback<2>,
	hcsr04::callback<3>,
	hcsr04::callback<4>,
	hcsr04::callback<5>,
	hcsr04::callback<6>,
	hcsr04::callback<7>,
	hcsr04::callback<8>,
	hcsr04::callback<9>,
	hcsr04::callback<10>,
	hcsr04::callback<11>,
	hcsr04::callback<12>,
	hcsr04::callback<13>,
	hcsr04::callback<14>,
	hcsr04::callback<15>,
	hcsr04::callback<16>,
	hcsr04::callback<17>,
	hcsr04::callback<18>,
	hcsr04::callback<19>,
	hcsr04::callback<20>,
	hcsr04::callback<21>,
	hcsr04::callback<22>,
	hcsr04::callback<23>,
	hcsr04::callback<24>,
	hcsr04::callback<25>,
	hcsr04::callback<26>,
	hcsr04::callback<27>,
	hcsr04::callback<28>,
	hcsr04::callback<29>,
	hcsr04::callback<30>,
	hcsr04::callback<31>
};

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
void Update( void *apInstance )
{
	auto phcsr = reinterpret_cast<hcsr04*>(apInstance);
	return phcsr->Update();
}

uint32_t Read( void *apInstance )
{
	auto phcsr = reinterpret_cast<hcsr04*>(apInstance);
	return phcsr->QTime();
}

} //extern "C"
