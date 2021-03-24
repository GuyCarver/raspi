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
// FILE    a3144lib.cpp
// BY      gcarver
// DATE    03/18/2021 11:04 AM
//----------------------------------------------------------------------

//Compiled with g++ -Wall -pthread -o a3144lib a3144lib.cpp -lpigpio -lrt

#include <cstdlib>
#include <cstdint>
#include <atomic>
#include <wiringPi.h>

//#define DEBUGOUT
#ifdef DEBUGOUT
#include <iostream>
#endif //DEBUGOUT

//The winringPi interrupt callback system doesn't have a payload, so we have
// to supply a unique function for each pin. This is the signature of the
// interrupt callback function.
typedef void (*cbFunction)(  );

// #define ATOMIC 1
#ifdef ATOMIC

using guyatomic = std::atomic<uint32_t>;

#else //ATOMIC

class guyatomic
{
public:
	guyatomic( uint32_t aValue ) : v(aValue) {  }
	uint32_t exchange( uint32_t aValue )
	{
		uint32_t ov = v;
		v = aValue;
		return ov;
	}

	uint32_t load(  ) const
	{
		return v;
	}

	void store( uint32_t aValue )
	{
		v = aValue;
	}

	uint32_t operator++(  )
	{
		return ++v;
	}
private:
	uint32_t v = 0;
};
#endif //ATOMIC

//--------------------------------------------------------
//Set pin connected to an a3144 hall effect sensor for interrupt on trigger.
// Keep track of the count and time between first trigger and the last.
// When read, the counter and times are reset.
// Input is 1 until magnet is in range, at which time it switches to 0 and triggers the interrupt.
//  The input returns 1 when the magnet goes out of range.
class hall
{
public:

	//--------------------------------------------------------
	hall( uint32_t aPin ) : Pin(aPin)
	{
		Startup();								// Make sure gpio system is initialized.

		hallArray[Pin] = this;

		//Setup the pin.
		pinMode(Pin, INPUT);
		pullUpDnControl(Pin, PUD_UP);			// Need a pull up resistor to put the pin at 1.

		//Set the ISR function to trigger on FALLING (Pin goes to 0).
		wiringPiISR(Pin, INT_EDGE_FALLING, callbacks[Pin]);
	}

	//--------------------------------------------------------
	~hall()
	{
		hallArray[Pin] = nullptr;
	}

	//--------------------------------------------------------
	const uint32_t *GetData(  )
	{
		Read[0] = Counter.exchange(0);
		uint32_t t = Time.load();
		uint32_t dt = t - First.exchange(0);	// Calc delta between first interupt and last.

		//If msb is set, the counter wrapped around so subtract from 0 to get the right value.
		// Can't just negate dt because it's an unsigned value.
		if (dt & 0x80000000) {
			dt = 0 - dt;
		}

		Read[1] = dt;
		return Read;
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

	//--------------------------------------------------------
	uint32_t Pin = 0;
	guyatomic Counter = {0};		// Current counter.
	guyatomic Time = {0};			// Current time.
	guyatomic First = {0};			// First time.
	uint32_t Read[2];							// Container to return the Counter and Timer to the calling Python.

	static bool bInitialized;					// Indicates if wiringPi has been initialized.
	static hall *hallArray[32];					// Array of hall objects by pin.
	static cbFunction callbacks[];				// Array of unique interrupt callback functions.

	//--------------------------------------------------------
	inline void trigger( uint32_t aTime )
	{
		++Counter;
		Time.store(aTime);
		if (First.load() == 0) {
			First = aTime;
		}
	}

	//--------------------------------------------------------
	template<uint32_t P> static void callback(  )
	{
#ifdef DEBUGOUT
		std::cout << "callback" << P << std::endl;
#endif //DEBUGOUT
		hall *phall = hallArray[P];
		if (phall) {
			phall->trigger(micros());
		}
	}
};

bool hall::bInitialized = false;
hall* hall::hallArray[] = { nullptr };

//--------------------------------------------------------
cbFunction hall::callbacks[] = {
	hall::callback<0>,
	hall::callback<1>,
	hall::callback<2>,
	hall::callback<3>,
	hall::callback<4>,
	hall::callback<5>,
	hall::callback<6>,
	hall::callback<7>,
	hall::callback<8>,
	hall::callback<9>,
	hall::callback<10>,
	hall::callback<11>,
	hall::callback<12>,
	hall::callback<13>,
	hall::callback<14>,
	hall::callback<15>,
	hall::callback<16>,
	hall::callback<17>,
	hall::callback<18>,
	hall::callback<19>,
	hall::callback<20>,
	hall::callback<21>,
	hall::callback<22>,
	hall::callback<23>,
	hall::callback<24>,
	hall::callback<25>,
	hall::callback<26>,
	hall::callback<27>,
	hall::callback<28>,
	hall::callback<29>,
	hall::callback<30>,
	hall::callback<31>
};

//Following are the external interface functions.
extern "C"
{

//--------------------------------------------------------
void *Create( uint32_t aPin )
{
	return new hall(aPin);
}

//--------------------------------------------------------
void Release( void *apHall )
{
	auto phall = reinterpret_cast<hall*>(apHall);
	delete phall;
}

//--------------------------------------------------------
const uint32_t *GetData( void *apHall )
{
	auto phall = reinterpret_cast<hall*>(apHall);
	return phall->GetData();
}

void Startup(  )
{
	hall::Startup();
}

} //extern "C"