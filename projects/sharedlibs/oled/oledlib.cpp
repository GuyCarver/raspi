//----------------------------------------------------------------------
// Copyright (c) 2021, gcarver
// All rights reserved.
//
// Redistribution and use in source and binary forms, with or without modification,
// are permitted provided that the following conditions are met:
//
//	 * Redistributions of source code must retain the above copyright notice,
//	   this list of conditions and the following disclaimer.
//
//	 * Redistributions in binary form must reproduce the above copyright notice,
//	   this list of conditions and the following disclaimer in the documentation
//	   and/or other materials provided with the distribution.
//
//	 * The name of Guy Carver may not be used to endorse or promote products derived
//	   from this software without specific prior written permission.
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
// FILE	oledlib.cpp
// BY	  gcarver
// DATE	03/06/2021 12:19 PM
//----------------------------------------------------------------------

//128x64 OLED display driver converted from Adafruit SSD1306 libraries.
//NOTE: I cannot get this to work. It doesn't throw any errors, but for some
// reason nothing works.  If I run the python version to enable the device I
// do see some changes to the display, but nothing correct.  However if the screen
// is blank it will remain so and no changes from running this will be shown.

#include <iostream>								//For std::cout
#include <cstdint>
#include <fcntl.h>								// For open.
#include <sys/ioctl.h>							// To set ioctl method on the open file
#include <linux/i2c-dev.h>						// For ISC_SLAVE
#include <unistd.h>								// For usleep, close
#include <cstring>								// For memset
#include <thread>
#include <mutex>
#include <condition_variable>

//NOTE: This current code will set the pixel at 0,0 but the scrolling will not scroll it.  Don't know if it's software causing it or not.

//TODO: Background thread, at least for display update.
//TODO: Multiple fonts
//TODO: Scrolling
//TODO: Multiple instances?

// Buffer layout in bits.  128 columns by 64 rows.
// Each byte represents 8 pixels in a row.
//	Column
//  R 0   8   10 ... 3F8
//  O 1   9   11 ... 3F9
//  W 2   A   12 ... 3FA
//	3   B   13 ... 3FB
//	4   C   14 ... 3FC
//	5   D   15 ... 3FD
//	6   E   16 ... 3FE
//	7   F   17 ... 3FF
//	400 408
//	401 409
//	402 40A
//	403 40B
//	404 40C
//	405 40D
//	406 40E
//	407 40F

//Make the following values visible to the outside.
extern const uint8_t STOP = 0;
extern const uint8_t LEFT = 1;
extern const uint8_t RIGHT = 2;
extern const uint8_t DIAGLEFT = 3;
extern const uint8_t DIAGRIGHT = 4;

//Indexes for the Fonts array used for text/char rendering.
extern const uint8_t TERMINAL = 0;
extern const uint8_t SYS = 1;
extern const uint8_t SERIF = 2;

//Include the fonts here.
#include "terminalfont.ipp"
#include "sysfont.ipp"
#include "seriffont.ipp"

namespace
{
	//--------------------------------------------------------
	//C++17 has a semaphore, but we aren't using C++17 yet, so here we have an uglier semaphore.
	class Semaphore
	{
	public:
		Semaphore ( uint32_t aCount = 0) : _count(aCount) {  }

		//--------------------------------------------------------
		void Notify(  )
		{
			std::unique_lock<std::mutex> lock(_mutex);
			_count++;
			//notify the waiting thread
			_cv.notify_one();
		}

		//--------------------------------------------------------
		void Wait(  )
		{
			std::unique_lock<std::mutex> lock(_mutex);
			while (_count == 0) {
				//wait on the mutex until notify is called
				_cv.wait(lock);
			}
			_count--;
		}

		//--------------------------------------------------------
		bool TryWait(  )
		{
			bool bres = (_count != 0);
			if (bres) {
				std::unique_lock<std::mutex> lock(_mutex);
				while (_count == 0) {
					//wait on the mutex until notify is called
					_cv.wait(lock);
				}
				_count--;
			}
			return bres;
		}

	private:
		std::mutex _mutex;
		std::condition_variable _cv;
		uint32_t _count;
	};

	constexpr uint8_t I2C_SMBUS_WRITE = 0;

	constexpr uint8_t I2C_SMBUS_I2C_BLOCK_DATA = 8u;
	constexpr uint32_t I2C_SMBUS_BLOCK_MAX = 32u; //As specified in SMBus standard

	constexpr uint8_t _ADDRESS = 0x3C;			// I2C address.

	constexpr uint8_t _CMDMODE = 0x00;
	constexpr uint8_t _DATAMODE = 0x40;
	constexpr uint8_t _SETCONTRAST = 0x81;
	constexpr uint8_t _DISPLAYALLON_RESUME = 0xA4;
	constexpr uint8_t _DISPLAYALLON = 0xA5;
	constexpr uint8_t _NORMALDISPLAY = 0xA6;
	constexpr uint8_t _INVERTDISPLAY = 0xA7;
	constexpr uint8_t _DISPLAYOFF = 0xAE;
	constexpr uint8_t _DISPLAYON = 0xAF;
	constexpr uint8_t _SETDISPLAYOFFSET = 0xD3;
	constexpr uint8_t _SETCOMPINS = 0xDA;
	constexpr uint8_t _SETVCOMDETECT = 0xDB;
	constexpr uint8_t _SETDISPLAYCLOCKDIV = 0xD5;
	constexpr uint8_t _SETPRECHARGE = 0xD9;
	constexpr uint8_t _SETMULTIPLEX = 0xA8;
	constexpr uint8_t _SETLOWCOLUMN = 0x00;
	constexpr uint8_t _SETHIGHCOLUMN = 0x10;
	constexpr uint8_t _SETSTARTLINE = 0x40;
	constexpr uint8_t _MEMORYMODE = 0x20;
	constexpr uint8_t _COLUMNADDR = 0x21;
	constexpr uint8_t _PAGEADDR = 0x22;
	constexpr uint8_t _COMSCANINC = 0xC0;
	constexpr uint8_t _COMSCANDEC = 0xC8;
	constexpr uint8_t _SEGREMAP = 0xA0;
	constexpr uint8_t _CHARGEPUMP = 0x8D;
	constexpr uint8_t _EXTRNALVCC = 0x1;
	constexpr uint8_t _SWITCHAPVCC = 0x2;
	constexpr uint8_t _ACTIVATE_SCROLL = 0x2F;
	constexpr uint8_t _DEACTIVATE_SCROLL = 0x2E;
	constexpr uint8_t _SET_VERTICAL_SCROLL_AREA = 0xA3;
	constexpr uint8_t _RIGHT_HORIZONTAL_SCROLL = 0x26;
	constexpr uint8_t _LEFT_HORIZONTAL_SCROLL = 0x27;
	constexpr uint8_t _VERTICAL_AND_RIGHT_HORIZONTAL_SCROLL = 0x29;
	constexpr uint8_t _VERTICAL_AND_LEFT_HORIZONTAL_SCROLL = 0x2A;

	//Array of fonts to use for text rendering.
	const uint8_t *Fonts[] = { terminalfont, sysfont, seriffont };

	//Commands to send during display.
	uint8_t _displayCommands[] =
	{
		_COLUMNADDR, 0, 0,
		_PAGEADDR, 0, 0
	};

	//Commands to send during init.
	uint8_t _initCommands[] =
	{
		_SETDISPLAYCLOCKDIV, 0x80,				// Suggested ratio
		_SETMULTIPLEX, 63, 						// static_cast<uint8_t>(aHeight - 1),
		_SETDISPLAYOFFSET, 0,
		_SETSTARTLINE,
		_CHARGEPUMP, 0x14,						// No external power
		_MEMORYMODE, 0,							// Act like ks0108
		_SEGREMAP + 1,
		_COMSCANDEC,
		_SETCOMPINS, 0x12,						// aHeight == static_cast<uint8_t>(64 ? 0x12u : 0x02u),
		_SETCONTRAST, 0x8F,						// _dim,
		_SETPRECHARGE, 0xF1,
		_SETVCOMDETECT, 0x40,
		_DISPLAYALLON_RESUME,
		_NORMALDISPLAY, 0xB0, 0x10, 0x01,		// Set original position to 0,0.
	};

}	//namespace

//--------------------------------------------------------
class oled
{
public:

	//--------------------------------------------------------
	oled( uint32_t aHeight = 64 )
	{
		_pinstance = this;

		_i2c = open("/dev/i2c-1", O_RDWR);
		if (_i2c < 0) {
			std::cout << "Error opening I2C device." << std::endl;
			return;
		}
		if (ioctl(_i2c, I2C_SLAVE, _ADDRESS) < 0) {		// Set the I2C address to use for this file descriptor.
			std::cout << "Error setting I2C device address." << std::endl;
			return;
		}

		_size[1] = aHeight;
		_pages = aHeight / 8;
		_bytes = _size[0] * _pages;
		_buffer[0] = new uint8_t[_bytes];
		_buffer[1] = new uint8_t[_bytes];
		memset(_buffer[0], 0, _bytes);
		memset(_buffer[1], 0, _bytes);
		Clear();

		//Set some values in the init command list.
		_initCommands[3] = static_cast<uint8_t>(aHeight - 1);
		_initCommands[14] = (aHeight == 64) ? 0x12u : 0x02u;
		_initCommands[16] = _dim;

		//Set some values in the display command list.
		_displayCommands[2] = _size[0] - 1;
		_displayCommands[5] = _pages - 1;

		//Send the init commands.
		SendCommands(_initCommands, sizeof(_initCommands));

		SetOn(true);
		Present();
		_presented.Notify();

		_pLoop = new std::thread([] () { _pinstance->MainLoop(); });

	}

	//--------------------------------------------------------
	~oled(  )
	{
		delete [] _buffer[0];
		delete [] _buffer[1];

		_bRunning = false;						// Turn off loop
		_present.Notify();						// Trigger the BG thread to run so it can exit
		_pLoop->join();							// Wait for _pLoop to exit
		delete _pLoop;

		close(_i2c);
		_pinstance = nullptr;
	}

	//--------------------------------------------------------
	const uint32_t *QSize(  ) const
	{
		return _size;
	}

	//--------------------------------------------------------
	void SetOn( bool aOn )
	{
		if (_on != aOn) {
			_on = aOn;
			SendCommand(_on ? _DISPLAYON : _DISPLAYOFF);
		}
	}

	//--------------------------------------------------------
	bool GetOn(  ) const { return _on; }

	//--------------------------------------------------------
	void SetInverted( bool aInverted )
	{
		if (_inverted != aInverted) {
			_inverted = aInverted;
			SendCommand(_inverted ? _INVERTDISPLAY : _NORMALDISPLAY);
		}
	}

	//--------------------------------------------------------
	bool GetInverted(  ) const { return _inverted; }

	//--------------------------------------------------------
	void SetRotation( uint8_t aRotation )
	{
		_rotation = aRotation & 0x03;
	}

	//--------------------------------------------------------
	uint8_t GetRotation(  ) const { return _rotation; }

	//--------------------------------------------------------
	void SetDim( uint8_t aValue )
	{
		_dim = aValue;
		SendCommand(_dim);
	}

	//--------------------------------------------------------
	uint8_t GetDim(  ) const { return _dim; }

	//--------------------------------------------------------
	void Fill( uint8_t aValue )
	{
		memset(_buffer[_index], aValue, _bytes);
	}

	//--------------------------------------------------------
	void Clear(  )
	{
		Fill(0);
	}

	//--------------------------------------------------------
	void Pixel( uint32_t aX, uint32_t aY, bool aOn )
	{
		uint32_t x, y;

		if ((aX >= 0) && (aX < _size[0]) && (aY >= 0) && (aY < _size[1])) {
			switch (_rotation) {
				case 1:
				{
					x = _size[0] - aY - 1;
					y = aX;
					break;
				}
				case 2:
				{
					x = _size[0] - aX - 1;
					y = _size[1] - aY - 1;
					break;
				}
				case 3:
				{
					x = aY;
					y = _size[1] - x - 1;
					break;
				}
				default:
					x = aX;
					y = aY;
					break;
			}

			uint8_t bit = 1 << (y % 8);
			uint32_t index = x + ((y >> 3) * _size[0]);
			if (aOn) {
				_buffer[_index][index] |= bit;
			}
			else {
				_buffer[_index][index] &= ~bit;
			}
		}
	}

	//--------------------------------------------------------
	void Line( uint32_t aSX, uint32_t aSY, uint32_t aEX, uint32_t aEY, bool aOn )
	{
		int32_t dx = static_cast<int32_t>(aEX) - static_cast<int32_t>(aSX);
		int32_t dy = static_cast<int32_t>(aEY) - static_cast<int32_t>(aSY);
		int32_t inx, iny;

		if (dx > 0) {
			inx = 1;
		}
		else {
			inx = -1;
			dx = -dx;
		}
		if (dy > 0) {
			iny = 1;
		}
		else {
			iny = -1;
			dy = -dy;
		}

		if (dx >= dy) {
			dy <<= 1;
			auto e = dy - dx;
			dx <<= 1;
			while (aSX != aEX) {
				Pixel(aSX, aSY, aOn);
				if (e >= 0) {
					aSY += iny;
					e -= dx;
				}
				e += dy;
				aSX += inx;
			}
		}
		else {
			dx <<= 1;
			auto e = dx - dy;
			dy <<= 1;
			while (aSY != aEY) {
				Pixel(aSX, aSY, aOn);
				if (e >= 0) {
					aSX += inx;
					e -= dy;
				}
				e += dx;
				aSY += iny;
			}
		}
	}

	//--------------------------------------------------------
	void FillRect( uint32_t aSX, uint32_t aSY, uint32_t aW, uint32_t aH, bool aOn )
	{
		auto ex = aSX + aW;
		for ( uint32_t i = aSY; i < aSY + aH; ++i) {
			Line(aSX, i, ex, i, aOn);
		}
	}

	//--------------------------------------------------------
	void Char( uint32_t aSX, uint32_t aSY, unsigned char aChar, bool aOn, uint8_t aFont, uint32_t aSzX = 1, uint32_t aSzY = 1 )
	{
		const uint8_t *pfont = Fonts[aFont];
		uint8_t startChar = pfont[2];
		uint8_t endChar = pfont[3];
		const uint8_t *charData = pfont + 4;

		if ((aChar >= startChar) && (aChar <= endChar)) {
			auto w = pfont[0];
			auto h = pfont[1];
			uint32_t ci = (aChar - startChar) * w;
			auto charA = charData + ci;
			auto px = aSX;
			if ((aSzX <= 1) && (aSzY <= 1)) {
				for ( uint32_t i = 0; i < w; ++i) {
					auto c = *charA++;
					auto py = aSY;
					for ( uint32_t j = 0; j < h; ++j) {
						if (c & 1) {
							Pixel(px, py, aOn);
						}
						++py;
						c >>= 1;
					}
					++px;
				}
			}
			else {	//Scale
				for ( uint32_t i = 0; i < w; ++i) {
					auto c = *charA++;
					auto py = aSY;
					for ( uint32_t j = 0; j < h; ++j) {
						if (c & 1) {
							FillRect(px, py, aSzX, aSzY, aOn);
						}
						py += aSzY;
						c >>= 1;
					}
					px += aSzX;
				}
			}
		}
	}

	//--------------------------------------------------------
	void Text( uint32_t aSX, uint32_t aSY, const char *apString, uint8_t aOn,
		uint8_t aFont, uint32_t aSzX = 1, uint32_t aSzY = 1 )
	{
		auto x = aSX;
		auto w = aSzX * Fonts[aFont][0] + 1;	// Width.
		//Loop until we hit the null terminator.
		while (*apString) {
			Char(x, aSY, *apString++, aOn, aFont, aSzX, aSzY);
			x += w;
			//We check > rather than >= to let the right (blank) edge of the
			// character print off the right of the screen.
			if (x + w > _size[0]) {
				aSY += aSzX * Fonts[aFont][1] + 1;
				x = aSX;
			}
		}
	}

	//--------------------------------------------------------
	void Display(  )
	{
		//Make sure presentation is complete before triggering a new one
		if (_presented.TryWait()) {
			//Trigger present semaphore
			_present.Notify();
		}
	}

	//--------------------------------------------------------
	void Scroll( uint8_t aDirection, uint8_t aStart, uint8_t aStop )
	{
		switch (aDirection) {
			case LEFT:
				ScrollLR(_LEFT_HORIZONTAL_SCROLL, aStart, aStop);
				break;
			case RIGHT:
				ScrollLR(_RIGHT_HORIZONTAL_SCROLL, aStart, aStop);
				break;
			case DIAGLEFT:
				ScrollDiag(_VERTICAL_AND_LEFT_HORIZONTAL_SCROLL, aStart, aStop);
				break;
			case DIAGRIGHT:
				ScrollDiag(_VERTICAL_AND_RIGHT_HORIZONTAL_SCROLL, aStart, aStop);
				break;
			case STOP:
			default:
				SendCommand(_DEACTIVATE_SCROLL);
				break;
		}
	}

	static oled *QInstance(  ) { return _pinstance; }

private:

	std::thread *_pLoop = nullptr;
	//NOTE: These would be better as semaphores, but the c++17 semaphore doesn't seem to be available.
	Semaphore _present;							// Signal to BG Thread to begin presentation
	Semaphore _presented;						// Signal from BG Thread that presentation is complete

	uint8_t *_buffer[2] = { nullptr, nullptr };
	
	int32_t _i2c = 0;
	uint32_t _size[2] = {128, 64};
	uint32_t _pages;
	uint32_t _bytes;
	uint32_t _index = 0;
	uint8_t _rotation = 0;
	uint8_t _dim = 0x8F;

	bool _inverted = false;
	bool _on = false;
	bool _bRunning = true;

	static oled *_pinstance;

	//--------------------------------------------------------
	void WriteBlockData( uint8_t aCommand, const uint8_t *aBuffer, uint32_t aElems )
	{
		uint8_t data[I2C_SMBUS_BLOCK_MAX + 2];
		i2c_smbus_ioctl_data args;

		args.read_write = I2C_SMBUS_WRITE;
		args.command = aCommand;
		args.size = I2C_SMBUS_I2C_BLOCK_DATA;
		args.data = reinterpret_cast<i2c_smbus_data*>(data);

		//Cut buffer into allowable sizes and send each block
		while (aElems) {
			uint32_t ds = std::min(I2C_SMBUS_BLOCK_MAX, aElems);
			uint32_t i = 0;
			aElems -= ds;
			data[i++] = static_cast<uint8_t>(ds);

			//Copy source buffer into the destination
			memcpy(&data[i], aBuffer, ds);
			aBuffer += ds;						// Next source location

			auto res = ioctl(_i2c, I2C_SMBUS, &args);

			if (res < 0) {
				std::cout << "Error" << std::endl;
			}
		}
	}

	//--------------------------------------------------------
	void SendData( const uint8_t *aBuffer, uint32_t aElems )
	{
		WriteBlockData(_DATAMODE, aBuffer, aElems);
	}

	//--------------------------------------------------------
	void SendCommands( const uint8_t *aBuffer, uint32_t aElems )
	{
		WriteBlockData(_CMDMODE, aBuffer, aElems);
	}

	//--------------------------------------------------------
	//Send a single command.
	void SendCommand( uint8_t aValue )
	{
		WriteBlockData(_CMDMODE, &aValue, 1);
	}

	//--------------------------------------------------------
	void Present(  )
	{
		//NOTE: It takes ~0.16 seconds on RASPI3 to send the buffer.
		SendCommands(_displayCommands, sizeof(_displayCommands));
		SendData(_buffer[_index], _bytes);
		_index = 1 - _index;					// Toggle the index.
		_presented.Notify();					// Signal present is done
	}

	//--------------------------------------------------------
	void ScrollLR( uint8_t aDirection, uint8_t aStart, uint8_t aStop )
	{
		uint8_t lrdata[8];

		lrdata[0] = aDirection;
		lrdata[1] = 0;
		lrdata[2] = aStart;
		lrdata[3] = 0;
		lrdata[4] = aStop;
		lrdata[5] = 0;
		lrdata[6] = 0xFF;
		lrdata[7] = _ACTIVATE_SCROLL;

		SendCommands(lrdata, sizeof(lrdata));
	}

	//--------------------------------------------------------
	void ScrollDiag( uint8_t aDirection, uint8_t aStart, uint8_t aStop )
	{
		uint8_t sdata[10];

		sdata[0] = _SET_VERTICAL_SCROLL_AREA;
		sdata[1] = 0;
		sdata[2] = static_cast<uint8_t>(_size[1]);
		sdata[3] = aDirection;
		sdata[4] = 0;
		sdata[5] = aStart;
		sdata[6] = 0;
		sdata[7] = aStop;
		sdata[8] = 1;
		sdata[9] = _ACTIVATE_SCROLL;

		SendCommands(sdata, sizeof(sdata));
	}

	//--------------------------------------------------------
	void MainLoop(  )
	{
		while (_bRunning) {
			_present.Wait();					// Wait for a present to be triggered
			if (_bRunning) {
				Present();
			}
		}
	}
};

oled *oled::_pinstance = nullptr;

// int32_t main(  )
// {
// 	auto g = oled();
// 	while (true) {
// 		auto m = g.GetMag();
// 		for ( uint32_t i = 0; i < 3; ++i) {
// 			std::cout << m[i] << ',';
// 		}
// 		std::cout << "				\r";
// 	}
// 	return 0;
// }

extern "C"
{

//--------------------------------------------------------
void Startup(  )
{
	if (oled::QInstance() == nullptr) {
		new oled();
	}
}

//--------------------------------------------------------
void Shutdown(  )
{
	auto p = oled::QInstance();
	if (p) {
		delete p;
	}
}

//--------------------------------------------------------
void Text( uint32_t aX, uint32_t aY, const char *apString, uint8_t aOn, uint8_t aFont, uint32_t aSzX, uint32_t aSzY )
{
	auto p = oled::QInstance();
	if (p) {
		if (aFont > 2) {
			aFont = 0;
		}
		p->Text(aX, aY, apString, aOn, aFont, aSzX, aSzY);
	}
}

//--------------------------------------------------------
void Char( uint32_t aSX, uint32_t aSY, unsigned char aChar, bool aOn,
	uint8_t aFont, uint32_t aSzX = 1, uint32_t aSzY = 1 )
{
	auto p = oled::QInstance();
	if (p) {
		if (aFont > 2) {
			aFont = 0;
		}
		p->Char(aSX, aSY, aChar, aOn, aFont, aSzX, aSzY);
	}
}

//--------------------------------------------------------
void FillRect( uint32_t aSX, uint32_t aSY, uint32_t aW, uint32_t aH, bool aOn )
{
	auto p = oled::QInstance();
	if (p) {
		p->FillRect(aSX, aSY, aW, aH, aOn);
	}
}

//--------------------------------------------------------
void Line( uint32_t aSX, uint32_t aSY, uint32_t aEX, uint32_t aEY, bool aOn )
{
	auto p = oled::QInstance();
	if (p) {
		p->Line(aSX, aSY, aEX, aEY, aOn);
	}
}

//--------------------------------------------------------
void Pixel( uint32_t aX, uint32_t aY, bool aOn )
{
	auto p = oled::QInstance();
	if (p) {
		p->Pixel(aX, aY, aOn);
	}
}

//--------------------------------------------------------
void Clear(  )
{
	auto p = oled::QInstance();
	if (p) {
		p->Clear();
	}
}

//--------------------------------------------------------
void Fill( uint8_t aValue )
{
	auto p = oled::QInstance();
	if (p) {
		p->Fill(aValue);
	}
}

//--------------------------------------------------------
void SetOn( bool aOn )
{
	auto p = oled::QInstance();
	if (p) {
		p->SetOn(aOn);
	}
}

//--------------------------------------------------------
bool GetOn(  )
{
	auto p = oled::QInstance();
	return p ? p->GetOn() : false;
}


//--------------------------------------------------------
void SetInverted( bool aInverted )
{
	auto p = oled::QInstance();
	if (p) {
		p->SetInverted(aInverted);
	}
}

//--------------------------------------------------------
bool GetInverted(  )
{
	auto p = oled::QInstance();
	return p ? p->GetInverted() : false;
}

//--------------------------------------------------------
void SetRotation( uint8_t aRotation )
{
	auto p = oled::QInstance();
	if (p) {
		p->SetRotation(aRotation);
	}
}

//--------------------------------------------------------
uint8_t GetRotation(  )
{
	auto p = oled::QInstance();
	return p ? p->GetRotation() : 0;
}

//--------------------------------------------------------
void SetDim( uint8_t aValue )
{
	auto p = oled::QInstance();
	if (p) {
		p->SetDim(aValue);
	}
}

//--------------------------------------------------------
uint8_t GetDim(  )
{
	auto p = oled::QInstance();
	return p ? p->GetDim() : 0;
}

//--------------------------------------------------------
void Display(  )
{
	auto p = oled::QInstance();
	if (p) {
		p->Display();
	}
}

//--------------------------------------------------------
const uint32_t *GetSize(  )
{
	static const uint32_t defsize[2] = {128, 64};
	auto p = oled::QInstance();
	return p != nullptr ? p->QSize() : defsize;
}

//--------------------------------------------------------
void Scroll( uint8_t aDirection, uint8_t aStart, uint8_t aStop )
{
	auto p = oled::QInstance();
	if (p) {
		p->Scroll(aDirection, aStart, aStop);
	}
}

} //extern "C"

#define _EXE 1
#ifdef _EXE

#include <ctime>
#include <ratio>
#include <chrono>

int32_t main(  )
{
	using namespace std::chrono;

	Startup();
	Fill(0xFF);

	high_resolution_clock::time_point t1 = high_resolution_clock::now();
	Text(0, 10, "Hello Guy!", 0, TERMINAL, 1, 1);
	high_resolution_clock::time_point t2 = high_resolution_clock::now();

	duration<double> time_span = duration_cast<duration<double>>(t2 - t1);
	std::cout << "Text Time: " << time_span.count() << " seconds.\n";

	t1 = high_resolution_clock::now();
	Display();
	t2 = high_resolution_clock::now();

	time_span = duration_cast<duration<double>>(t2 - t1);

	std::cout << "Display Time: " << time_span.count() << " seconds.\n";

	usleep(4000000);
	Shutdown();

	return 0;
}
#endif //_EXE
