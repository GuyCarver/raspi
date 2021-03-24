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
// FILE    oled.cpp
// BY      gcarver
// DATE    03/06/2021 12:19 PM
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

//NOTE: This current code will set the pixel at 0,0 but the scrolling will not scroll it.  Don't know if it's software causing it or not.

// Buffer layout in bits.  128 columns by 64 rows.
// Each byte represents 8 pixels in a row.
//    Column
//  R 0   8   10 ... 3F8
//  O 1   9   11 ... 3F9
//  W 2   A   12 ... 3FA
//    3   B   13 ... 3FB
//    4   C   14 ... 3FC
//    5   D   15 ... 3FD
//    6   E   16 ... 3FE
//    7   F   17 ... 3FF
//    400 408
//    401 409
//    402 40A
//    403 40B
//    404 40C
//    405 40D
//    406 40E
//    407 40F

//Make the following values visible to the outside.
extern "C"
{
	const uint32_t STOP = 0;
	const uint32_t LEFT = 1;
	const uint32_t RIGHT = 2;
	const uint32_t DIAGLEFT = 3;
	const uint32_t DIAGRIGHT = 3;
} //extern "C"

namespace
{
	constexpr uint8_t I2C_SMBUS_WRITE = 0;

	constexpr uint8_t I2C_SMBUS_BLOCK_DATA = 5u;
	constexpr uint32_t I2C_SMBUS_BLOCK_MAX = 32u; //As specified in SMBus standard

	//w, h, start (ascii), end (ascii), data...
	uint8_t terminalfont[] = {6, 8, 31, 127,
		0x20, 0x3E, 0x61, 0x61, 0x3E, 0x20, //#Bell icon at 0x31.
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x06, 0x5F, 0x06, 0x00,
		0x00, 0x07, 0x03, 0x00, 0x07, 0x03,
		0x00, 0x24, 0x7E, 0x24, 0x7E, 0x24,
		0x00, 0x24, 0x2B, 0x6A, 0x12, 0x00,
		0x00, 0x63, 0x13, 0x08, 0x64, 0x63,
		0x00, 0x36, 0x49, 0x56, 0x20, 0x50,
		0x00, 0x00, 0x07, 0x03, 0x00, 0x00,
		0x00, 0x00, 0x3E, 0x41, 0x00, 0x00,
		0x00, 0x00, 0x41, 0x3E, 0x00, 0x00,
		0x00, 0x08, 0x3E, 0x1C, 0x3E, 0x08,
		0x00, 0x08, 0x08, 0x3E, 0x08, 0x08,
		0x00, 0x00, 0xE0, 0x60, 0x00, 0x00,
		0x00, 0x08, 0x08, 0x08, 0x08, 0x08,
		0x00, 0x00, 0x60, 0x60, 0x00, 0x00,
		0x00, 0x20, 0x10, 0x08, 0x04, 0x02,
		0x00, 0x3E, 0x51, 0x49, 0x45, 0x3E,
		0x00, 0x00, 0x42, 0x7F, 0x40, 0x00,
		0x00, 0x62, 0x51, 0x49, 0x49, 0x46,
		0x00, 0x22, 0x49, 0x49, 0x49, 0x36,
		0x00, 0x18, 0x14, 0x12, 0x7F, 0x10,
		0x00, 0x2F, 0x49, 0x49, 0x49, 0x31,
		0x00, 0x3C, 0x4A, 0x49, 0x49, 0x30,
		0x00, 0x01, 0x71, 0x09, 0x05, 0x03,
		0x00, 0x36, 0x49, 0x49, 0x49, 0x36,
		0x00, 0x06, 0x49, 0x49, 0x29, 0x1E,
		0x00, 0x00, 0x6C, 0x6C, 0x00, 0x00,
		0x00, 0x00, 0xEC, 0x6C, 0x00, 0x00,
		0x00, 0x08, 0x14, 0x22, 0x41, 0x00,
		0x00, 0x24, 0x24, 0x24, 0x24, 0x24,
		0x00, 0x00, 0x41, 0x22, 0x14, 0x08,
		0x00, 0x02, 0x01, 0x59, 0x09, 0x06,
		0x00, 0x3E, 0x41, 0x5D, 0x55, 0x1E,
		0x00, 0x7E, 0x11, 0x11, 0x11, 0x7E,
		0x00, 0x7F, 0x49, 0x49, 0x49, 0x36,
		0x00, 0x3E, 0x41, 0x41, 0x41, 0x22,
		0x00, 0x7F, 0x41, 0x41, 0x41, 0x3E,
		0x00, 0x7F, 0x49, 0x49, 0x49, 0x41,
		0x00, 0x7F, 0x09, 0x09, 0x09, 0x01,
		0x00, 0x3E, 0x41, 0x49, 0x49, 0x7A,
		0x00, 0x7F, 0x08, 0x08, 0x08, 0x7F,
		0x00, 0x00, 0x41, 0x7F, 0x41, 0x00,
		0x00, 0x30, 0x40, 0x40, 0x40, 0x3F,
		0x00, 0x7F, 0x08, 0x14, 0x22, 0x41,
		0x00, 0x7F, 0x40, 0x40, 0x40, 0x40,
		0x00, 0x7F, 0x02, 0x04, 0x02, 0x7F,
		0x00, 0x7F, 0x02, 0x04, 0x08, 0x7F,
		0x00, 0x3E, 0x41, 0x41, 0x41, 0x3E,
		0x00, 0x7F, 0x09, 0x09, 0x09, 0x06,
		0x00, 0x3E, 0x41, 0x51, 0x21, 0x5E,
		0x00, 0x7F, 0x09, 0x09, 0x19, 0x66,
		0x00, 0x26, 0x49, 0x49, 0x49, 0x32,
		0x00, 0x01, 0x01, 0x7F, 0x01, 0x01,
		0x00, 0x3F, 0x40, 0x40, 0x40, 0x3F,
		0x00, 0x1F, 0x20, 0x40, 0x20, 0x1F,
		0x00, 0x3F, 0x40, 0x3C, 0x40, 0x3F,
		0x00, 0x63, 0x14, 0x08, 0x14, 0x63,
		0x00, 0x07, 0x08, 0x70, 0x08, 0x07,
		0x00, 0x71, 0x49, 0x45, 0x43, 0x00,
		0x00, 0x00, 0x7F, 0x41, 0x41, 0x00,
		0x00, 0x02, 0x04, 0x08, 0x10, 0x20,
		0x00, 0x00, 0x41, 0x41, 0x7F, 0x00,
		0x00, 0x04, 0x02, 0x01, 0x02, 0x04,
		0x80, 0x80, 0x80, 0x80, 0x80, 0x80,
		0x00, 0x00, 0x03, 0x07, 0x00, 0x00,
		0x00, 0x20, 0x54, 0x54, 0x54, 0x78,
		0x00, 0x7F, 0x44, 0x44, 0x44, 0x38,
		0x00, 0x38, 0x44, 0x44, 0x44, 0x28,
		0x00, 0x38, 0x44, 0x44, 0x44, 0x7F,
		0x00, 0x38, 0x54, 0x54, 0x54, 0x08,
		0x00, 0x08, 0x7E, 0x09, 0x09, 0x00,
		0x00, 0x18, 0xA4, 0xA4, 0xA4, 0x7C,
		0x00, 0x7F, 0x04, 0x04, 0x78, 0x00,
		0x00, 0x00, 0x00, 0x7D, 0x40, 0x00,
		0x00, 0x40, 0x80, 0x84, 0x7D, 0x00,
		0x00, 0x7F, 0x10, 0x28, 0x44, 0x00,
		0x00, 0x00, 0x00, 0x7F, 0x40, 0x00,
		0x00, 0x7C, 0x04, 0x18, 0x04, 0x78,
		0x00, 0x7C, 0x04, 0x04, 0x78, 0x00,
		0x00, 0x38, 0x44, 0x44, 0x44, 0x38,
		0x00, 0xFC, 0x44, 0x44, 0x44, 0x38,
		0x00, 0x38, 0x44, 0x44, 0x44, 0xFC,
		0x00, 0x44, 0x78, 0x44, 0x04, 0x08,
		0x00, 0x08, 0x54, 0x54, 0x54, 0x20,
		0x00, 0x04, 0x3E, 0x44, 0x24, 0x00,
		0x00, 0x3C, 0x40, 0x20, 0x7C, 0x00,
		0x00, 0x1C, 0x20, 0x40, 0x20, 0x1C,
		0x00, 0x3C, 0x60, 0x30, 0x60, 0x3C,
		0x00, 0x6C, 0x10, 0x10, 0x6C, 0x00,
		0x00, 0x9C, 0xA0, 0x60, 0x3C, 0x00,
		0x00, 0x64, 0x54, 0x54, 0x4C, 0x00,
		0x00, 0x08, 0x3E, 0x41, 0x41, 0x00,
		0x00, 0x00, 0x00, 0x77, 0x00, 0x00,
		0x00, 0x00, 0x41, 0x41, 0x3E, 0x08,
		0x00, 0x02, 0x01, 0x02, 0x01, 0x00,
		0x00, 0x3C, 0x26, 0x23, 0x26, 0x3C
	};

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

	uint8_t _displayCommands[] =
	{
		_COLUMNADDR, 0, 0,
		_PAGEADDR, 0, 0
	};

	uint8_t _initCommands[] =
	{
// 		_DISPLAYOFF,
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
// 		_DISPLAYON
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
		_buffer = new uint8_t[_bytes];
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

// 		_on = true;				//Put this in if the display off/on commands are added to _initCommands array.
		SetOn(true);
		Display();

// 		_pLoop = new std::thread([] () { _pinstance->MainLoop(); });
	}

	//--------------------------------------------------------
	~oled(  )
	{
		delete [] _buffer;

// 		_bRunning = false;						// Turn off loop.
// 		_pLoop->join();							// Wait for _pLoop to exit.
// 		delete _pLoop;

		close(_i2c);
		_pinstance = nullptr;
	}

	//--------------------------------------------------------
	void SetOn( bool aOn )
	{
		if (_on != aOn) {
			_on = aOn;
			uint8_t v = _on ? _DISPLAYON : _DISPLAYOFF;
			SendCommands(&v, 1);
		}
	}

	//--------------------------------------------------------
	void SetInverted( bool aInverted )
	{
		if (_inverted != aInverted) {
			_inverted = aInverted;
			uint8_t v = _inverted ? _INVERTDISPLAY : _NORMALDISPLAY;
			SendCommands(&v, 1);
		}
	}

	//--------------------------------------------------------
	void SetRotation( uint8_t aRotation )
	{
		_rotation = aRotation & 0x03;
	}

	//--------------------------------------------------------
	void SetDim( uint8_t aValue )
	{
		_dim = aValue;
		SendCommands(&_dim, 1);
	}

	//--------------------------------------------------------
	void Fill( uint8_t aValue )
	{
		memset(_buffer, aValue, _bytes);
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
				_buffer[index] |= bit;
			}
			else {
				_buffer[index] &= ~bit;
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
	void Char( uint32_t aSX, uint32_t aSY, unsigned char aChar, bool aOn, uint8_t *apFont, uint32_t aSzX = 1, uint32_t aSzY = 1 )
	{
		auto startChar = apFont[2];
		auto endChar = apFont[3];
		auto charData = apFont + 4;

		if ((aChar >= startChar) && (aChar <= endChar)) {
			auto w = apFont[0];
			auto h = apFont[1];
			uint32_t ci = (aChar - startChar) * w;
			auto charA = charData + ci;
			auto px = aSX;
			if ((aSzX <= 1) && (aSzY <= 1)) {
				for ( uint32_t i = 0; i < w; ++i) {
					auto c = *charA++;
					auto py = aSY;
					for ( uint32_t j = 0; j < h; ++j) {
						if (c && 1) {
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
						if (c && 1) {
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
	void Text( uint32_t aSX, uint32_t aSY, const char *apString, uint8_t aColor,
		uint8_t *apFont, uint32_t aSzX = 1, uint32_t aSzY = 1 )
	{
		auto fontData = apFont + 4;
		auto x = aSX;
		auto w = aSzX * apFont[0] + 1;			// Width.
		//Loop until we hit the null terminator.
		while (*apString) {
			Char(x, aSY, *apString++, aColor, apFont, aSzX, aSzY);
			x += w;
			//We check > rather than >= to let the right (blank) edge of the
			// character print off the right of the screen.
			if (x + w > _size[0]) {
				aSY += aSzX * apFont[1] + 1;
				x = aSX;
			}
		}
	}

	//--------------------------------------------------------
	void Display(  )
	{
		//Send the command array.
		SendCommands(_displayCommands, sizeof(_displayCommands));
// 		uint32_t tosend = _bytes;
// 		auto pdata = _buffer;
// 		while (tosend) {
// 			uint32_t ds = std::min(32u, tosend);
// 			tosend -= ds;
// 			SendData(pdata, ds);
// 			pdata += ds;
// 		}
 		SendData(_buffer, _bytes);
	}

	static oled *QInstance(  ) { return _pinstance; }

private:

// 	std::thread *_pLoop = nullptr;
// 	std::mutex _suspend;

	uint8_t *_buffer = nullptr;
	
	int32_t _i2c = 0;
	uint32_t _size[2] = {128, 64};
	uint32_t _pages;
	uint32_t _bytes;
	uint8_t _rotation = 0;
	uint8_t _dim = 0x8F;

	bool _inverted = false;
	bool _on = false;

// 	bool _bRunning = true;

	static oled *_pinstance;

	//--------------------------------------------------------
	void WriteBlockData( uint8_t aCommand, uint8_t *aBuffer, uint32_t aElems )
	{
		uint8_t data[I2C_SMBUS_BLOCK_MAX + 2];
		i2c_smbus_ioctl_data args;

		args.read_write = I2C_SMBUS_WRITE;
		args.command = aCommand;
		args.size = I2C_SMBUS_BLOCK_DATA;
		args.data = reinterpret_cast<i2c_smbus_data*>(data);

		while (aElems) {
			uint32_t ds = std::min(I2C_SMBUS_BLOCK_MAX, aElems);
			uint32_t i = 0;
			aElems -= ds;
			data[i++] = ds;
			//Copy buffer into the data buffer.
			for ( ; i < ds; ++i) {
				data[i] = *aBuffer++;
			}
			auto res = ioctl(_i2c, I2C_SMBUS, &args);
			if (res < 0) {
				std::cout << "Error" << std::endl;
			}
		}
	}

	//--------------------------------------------------------
	void SendData( uint8_t *aBuffer, uint32_t aElems )
	{
		WriteBlockData(_DATAMODE, aBuffer, aElems);
	}

	//--------------------------------------------------------
	void SendCommands( uint8_t *aBuffer, uint32_t aElems )
	{
		WriteBlockData(_CMDMODE, aBuffer, aElems);
	}

	//--------------------------------------------------------
// 	void MainLoop(  )
// 	{
// 		while(_bRunning) {
// //TODO: Wait on semaphore
// 			_suspend.lock();
// 			UpdateAccelTempRot();
// 			UpdateMag();
// 			_suspend.unlock();
// 		}
// 	}
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
// 		std::cout << "                \r";
// 	}
// 	return 0;
// }

extern "C"
{

//--------------------------------------------------------
void Startup(  )
{
	if (oled::QInstance() == nullptr) {
		auto p = new oled();
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
void Text( float aX, float aY, const char *apString, uint8_t aColor, uint32_t aSzX, uint32_t aSzY )
{
	auto p = oled::QInstance();
	if (p) {
		p->Text(aX, aY, apString, aColor, terminalfont, aSzX, aSzY);
	}
}

//--------------------------------------------------------
void Char( uint32_t aSX, uint32_t aSY, unsigned char aChar, bool aOn,
	uint8_t *apFont, uint32_t aSzX = 1, uint32_t aSzY = 1 )
{
	auto p = oled::QInstance();
	if (p) {
		p->Char(aSX, aSY, aChar, aOn, terminalfont, aSzX, aSzY);
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
void SetInverted( bool aInverted )
{
	auto p = oled::QInstance();
	if (p) {
		p->SetInverted(aInverted);
	}
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
void SetDim( uint8_t aValue )
{
	auto p = oled::QInstance();
	if (p) {
		p->SetDim(aValue);
	}
}

//--------------------------------------------------------
void Display(  )
{
	auto p = oled::QInstance();
	if (p) {
		p->Display();
	}
}

} //extern "C"

int32_t main(  )
{
	Startup();
	Fill(0x3F);
// 	Text(0, 0, "Hi", 0xFF, 1, 1);
	Display();
	usleep(4000000);
	Shutdown();
	return 0;
}
