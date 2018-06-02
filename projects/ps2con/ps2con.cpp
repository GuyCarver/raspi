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
#include <python3.5/Python.h>
#include <python3.5/structmember.h>
#include <iostream>
#include <stdio.h>
#include <wiringPi.h>

#define Offset(Class,Member) (Py_ssize_t)((&((Class*)0)->Member) - 0)

static const unsigned char cmd_qmode[] = {1,0x41,0,0,0};			//Add the below bytes in to read analog (analog button mode needs to be set)
static const unsigned char cmd_qdata[] = {1,0x42,0,0,0,0,0,0,0};	//,0,0,0,0,0,0,0,0,0,0,0,0,0)
static const unsigned char cmd_enter_config[] = {1,0x43,0,1,0};
static const unsigned char cmd_exit_config[] = {1,0x43,0,0,0x5A,0x5A,0x5A,0x5A,0x5A};
static const unsigned char cmd_set_mode[] = {1,0x44,0,1,3,0,0,0,0};	//1 = analog stick mode, 3 = lock mode button.

//Button values. Bit 1 = changed, Bit 0 = Down state.
enum VALUES {
	UP,
	DOWN,										//Button is down.
	RELEASED,									//Indiciates button was just released.
	PRESSED										//Indicate button was just pressed.
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
	SQUARE
};

//_joys array indexes.
enum JOYS {
	RX = 0x10,									//This is just after BUTTONS::SQUARE.
	RY,
	LX,
	LY
};

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
/// <summary> This is an iterator for the ps2con::_buttons array.  It iterates
///  over the Buttons entries.  The system will get an iterator from ps2con
///  then the "next" call is on this iterator itself.  So the iterator holds
///  a pointer to the source ps2con instance and the current index. </summary>
///
class ButtonsIter : public PyObject
{
public:

	void Init( ps2con *apSource ) {
		_index = 0;
		_psource = apSource;
		Py_XINCREF(_psource);
	}

	//Body is below ps2con class definition.
	int32_t Get(  );

	static void Kill( ButtonsIter *apSelf ) {
		Py_XDECREF(apSelf->_psource);
		PyObject_DEL(apSelf);
	}

	//Body os below "ButtonsIter_type" definition.
	static PyObject *Create( ps2con *apSource );

	static PyObject *Next( ButtonsIter *apIter ) {
		if (apIter->_index > BUTTONS::SQUARE) {
			PyErr_SetNone(PyExc_StopIteration);
			return nullptr;
		}

		return Py_BuildValue("I", apIter->Get());
	}

	uint32_t _index;							//Iterator index.
	ps2con *_psource;							//Source of data we will iterate over.
};

static PyTypeObject ButtonsIter_type =
{
	PyVarObject_HEAD_INIT(&PyType_Type, sizeof(ButtonsIter))	//Type, size
	"ButtonsIter",								//tp_name
	sizeof(ButtonsIter),						//tp_basicsize
};

//Create iterator instance and set it's source pointer to the given ps2con instance.
PyObject *ButtonsIter::Create( ps2con *apSource )
{
	auto piter = PyObject_NEW(ButtonsIter, &ButtonsIter_type);
	piter->Init(apSource);
	return piter;
}

///
/// <summary> ps2 controller driver object. </summary>
///
class ps2con : public PyObject
{
public:

	bool Init( uint32_t aCmd, uint32_t aData, uint32_t aClk, uint32_t aAtt, PyObject *apCallback ) {
		_cmd = aCmd;
		_data = aData;
		_clk = aClk;
		_att = aAtt;
		_callback = nullptr;

		if (apCallback && (apCallback != Py_None) && !PyCallable_Check(apCallback)) {
			PyErr_SetString(PyExc_RuntimeError, "Incorrect params.  Expect callable object");
			return false;
		}

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
		DelayUS(3);

		//Read data a few times to settle out state changes.  Don't know why more than
		// a couple are needed but 6 is the minimum to be safe.
		for ( uint32_t i = 0; i < 6; ++i) {
			GetData();
			DelayUS(100);
		}

		DoSetCallback(apCallback);

		return true;
	}

	static void DelayUS( uint32_t us ) {
		delayMicroseconds(us);
	}

	static void SetPin( uint32_t aPin, bool aValue ) {
		digitalWrite(aPin, aValue ? HIGH : LOW);
	}

	static bool GetPin( uint32_t aPin ) {
		auto v = digitalRead(aPin);
		return (v != 0);
	}

	void DoSetCallback( PyObject *apCallback ) {
		Py_XDECREF(_callback);
		_callback = nullptr;
		if (PyCallable_Check(apCallback)) {
			_callback = apCallback;
			Py_XINCREF(apCallback);
		}
	}

	//Send given data and receive into _res array.
	void SendReceive( const uint8_t *apData, uint32_t aLen ) {
		SetPin(_att, false);					//Set self->_att to 0 to tell controller we are going to send.
		DelayUS(1);

		//Loop through all of the characters and send them.
		for ( uint32_t i = 0; i < aLen; ++i) {
			uint8_t value = 0;
			uint8_t snd = apData[i];

			for ( uint32_t j = 0; j < 8; ++j) {
				//Set self->_cmd to high if snd & 1
				SetPin(_cmd, (snd & 1) != 0);
				snd >>= 1;
				SetPin(_clk, false);			//Set _clk low.
				DelayUS(8);					//Delay must be at least 5 to work.
				value |= GetPin(_data) << j;
				SetPin(_clk, true);			//set _clk high.
				DelayUS(8);					//Delay must be at least 5 to work.
			}
			_res[i] = value;					//Store the read value into result buffer.
		}
		SetPin(_att, true);					//Set self->_att to 1.
		DelayUS(3);							//Delay just in case.
	}

	//Read data and process into _buttons and _joys arrays.
	void GetData(  ) {
		SendReceive(cmd_qdata, sizeof(cmd_qdata));

		//Double buffer button input so we can check for state changes.
		uint32_t prev = _prevbuttons;
		uint32_t b = _res[3] | (_res[4] << 8);
		_prevbuttons = b;						//Set new prev buttons for next time.
		for ( uint32_t i = 0; i <= SQUARE; ++i) {
			uint8_t bv = !(b & 1);
			//If == then value changed because the prev check doesn't negate the bit like bv setting above.
			if (bv == (prev & 1)) {
				bv |= RELEASED;					//Bit 1 set = changed state.  Bit 0 = up/down state.
			}
			_buttons[i] = bv;

			//If value not _UP and we have a callback function, then call it.
			if (bv && (_callback != nullptr)) {
//				auto pargs = PyTuple_New(2);
//				auto pybutton = Py_BuildValue("I", i);
//				auto pyvalue = Py_BuildValue("I", bv);
//				PyTuple_SetItem(pargs, 0, pybutton);
//				PyTuple_SetItem(pargs, 1, pyvalue);
				auto pargs = Py_BuildValue("ii", i, bv);
				//TODO: See about determing wether to call PyObject_CallFunction or CallObject.
				auto res = PyObject_CallObject(_callback, pargs);
				Py_DECREF(pargs);
				if (res != nullptr) {
					Py_DECREF(res);
				}
			}
			b >>= 1;
			prev >>= 1;
		}

		int32_t sgn = 1;
		//Loop through joystick input and change values 0-255 to +/- 255 with 0 in the middle.
		for ( uint32_t i = 5; i < 9; ++i) {
			_joys[i - 5] = ((_res[i] - 0x80) << 1) * sgn;
			sgn = -sgn;							//Every other input (y) needs to be reversed.
		}
	}

	uint32_t _cmd = 0;
	uint32_t _data = 0;
	uint32_t _clk = 0;
	uint32_t _att = 0;

	PyObject *_callback = nullptr;

	uint32_t _prevbuttons = 0;
	int32_t _joys[4];
	uint8_t _buttons[16];
	uint8_t _res[sizeof(cmd_qdata)];

//Following are the static Python interface methods.

	static const char *Name;

	//Body after ps2con_type definition below.
	static PyObject *Create( PyObject */*apSelf*/, PyObject *apArgs );

	static void Kill( ps2con *apSelf ) {
		apSelf->DoSetCallback(nullptr);
		PyObject_DEL(apSelf);
	}

	static PyObject *Update( ps2con *apSelf ) {
		apSelf->GetData();
		Py_RETURN_NONE;
	}

	//Function used for python ps2con() functionality using ps2con as a callable object.
	static PyObject *Call( ps2con *apSelf, PyObject *apArgs, PyObject *kw ) {
		return GetButton(apSelf, apArgs);
	}

	//Get button value given an index.
	static PyObject *GetButton( ps2con *apSelf, PyObject *apArg ) {
		int32_t index = PyLong_AsLong(apArg);

		if ((index < 0) || (index > SQUARE)) {
			PyErr_Format(PyExc_RuntimeError, "Button index %d out of range.", index);
			return nullptr;
		}

		return Py_BuildValue("I", apSelf->_buttons[index]);
	}

	//Get joystick value given an index.
	static PyObject *GetJoy( ps2con *apSelf, PyObject *apArg ) {
		//If the input values are _LX etc, they have an additional bit set to start them at index 16.  Strip that off.
		int32_t index = PyLong_AsLong(apArg) & 0x03;

		return Py_BuildValue("i", apSelf->_joys[index]);
	}

	//Set/Get callback functions.
	static PyObject *GetCallback( ps2con *apSelf, void * ) {
		if (apSelf->_callback) {
			return apSelf->_callback;
		}
		Py_RETURN_NONE;
	}

	static int32_t SetCallback( ps2con *apSelf, PyObject *apArg, void * ) {
		//Make sure apArg is callable.
		if ((apArg != Py_None) && !PyCallable_Check(apArg)) {
			PyErr_SetString(PyExc_RuntimeError, "Incorrect params.  Expect callable object");
			return 1;							//Error.
		}

		apSelf->DoSetCallback(apArg);

		return 0;								//ok
	}

	static PyObject *GetName( ps2con *, PyObject *apArg ) {
		int32_t index = PyLong_AsLong(apArg);

		if ((index < 0) || (index > JOYS::LY)) {
			PyErr_Format(PyExc_RuntimeError, "Button/Joystick index %d out of range.", index);
			return nullptr;
		}

		return Py_BuildValue("s", Names[index]);
	}

	//Create the ButtonsIter instance.
	static PyObject *ButtonsIter( ps2con *apSelf ) {
		return ButtonsIter::Create(apSelf);
	}

	//str() conversion function.
	static PyObject *Print( ps2con *apSelf ) {
		char mystring[256];
		sprintf(mystring, "ps2con._data = %X,%X,%X,%X,%X,%X,%X,%X,%X",
			apSelf->_res[0],
			apSelf->_res[1],
			apSelf->_res[2],
			apSelf->_res[3],
			apSelf->_res[4],
			apSelf->_res[5],
			apSelf->_res[6],
			apSelf->_res[7],
			apSelf->_res[8]
			);
		return(Py_BuildValue("s", mystring));
	}

};

const char *ps2con::Name = "ps2con";

//Type structure for ps2con class.  Other members are set in PyInit_ps2con() below.
static PyTypeObject ps2con_type =
{
	PyVarObject_HEAD_INIT(&PyType_Type, sizeof(ps2con))	//Type, size
	ps2con::Name,									//tp_name
	sizeof(ps2con),								//tp_basicsize
};

PyObject *ps2con::Create( PyObject */*apSelf*/, PyObject *apArgs )
{
	wiringPiSetupGpio();

	uint32_t cmd, data, clk, att;
	PyObject *pcallback = nullptr;

	if (!PyArg_ParseTuple(apArgs, "iiii|O", &cmd, &data, &clk, &att, &pcallback)) {
		return nullptr;
	}

	auto pcon = PyObject_NEW(ps2con, &ps2con_type);

	//If error in initialization exit with error.
	if (!pcon->Init(cmd, data, clk, att, pcallback)) {
		Py_DECREF(pcon);
		pcon = nullptr;
	}

	return pcon;
}

//Get button from source for the iterator's index and increment the index.
int32_t ButtonsIter::Get(  )
{
	return _psource->_buttons[_index++];
}

extern "C" {

	//List of methods for ps2con.ps2con object.
	static PyMethodDef ps2con_methods[] = {
		{"update", reinterpret_cast<PyCFunction>(ps2con::Update), METH_NOARGS, "Read controller input."},
		{"getbutton", reinterpret_cast<PyCFunction>(ps2con::GetButton), METH_O, "getbutton(index)"},
		{"getjoy", reinterpret_cast<PyCFunction>(ps2con::GetJoy), METH_O, "getjoy(index)"},
		{"getname", reinterpret_cast<PyCFunction>(ps2con::GetName), METH_O, "getname(index)"},
		{ nullptr, nullptr, 0, nullptr }
	};

	//List of members ot ps2con.ps2con object.  This is the simplest way to add access to member variables.
	// Next is the getters and setters shown below.  All of these members are read only.
	static PyMemberDef ps2con_members[] = {
		{"_cmd", T_INT, Offset(ps2con, _cmd), 1, "Command pin #" },
		{"_data", T_INT, Offset(ps2con, _data), 1, "Data pin #" },
		{"_clk", T_INT, Offset(ps2con, _clk), 1, "Clock pin #" },
		{"_att", T_INT, Offset(ps2con, _att), 1, "Attention pin #" },
		{ nullptr, 0, 0, 0, nullptr }
	};

	//List of properties for ps2con.ps2con object.
	static PyGetSetDef ps2con_getsets[] = {
		{"callback", reinterpret_cast<getter>(&ps2con::GetCallback), reinterpret_cast<setter>(&ps2con::SetCallback), "Callback function", nullptr },
		{ nullptr, nullptr, nullptr, nullptr, nullptr }
	};

	static PyMethodDef module_methods[] = {
		{ps2con::Name, reinterpret_cast<PyCFunction>(ps2con::Create), METH_VARARGS, "ps2con(cmd, data, clk, att, [callback])"},
		{NULL, NULL, 0, NULL}
	};

	PyMODINIT_FUNC PyInit_ps2con(  )
	{
		//Setup members of ps2con_type.
		ps2con_type.tp_methods = ps2con_methods;
		ps2con_type.tp_members = ps2con_members;
		ps2con_type.tp_getset = ps2con_getsets;
		ps2con_type.tp_dealloc = reinterpret_cast<destructor>(ps2con::Kill);
		ps2con_type.tp_call = reinterpret_cast<ternaryfunc>(ps2con::Call);
		ps2con_type.tp_str = reinterpret_cast<reprfunc>(ps2con::Print);
		ps2con_type.tp_iter = reinterpret_cast<getiterfunc>(ps2con::ButtonsIter);	//ps2con creates the ButtonsIter object.
		ps2con_type.tp_doc = "Testing the doc string for ps2con.ps2con.";

		//Member of ButtonsIter_type
		ButtonsIter_type.tp_iternext = reinterpret_cast<iternextfunc>(ButtonsIter::Next);  //But then the iterator object does the iteration.
		ButtonsIter_type.tp_dealloc = reinterpret_cast<destructor>(ButtonsIter::Kill);

		//Must call these or the objects won't work correctly (functions will not be available).
		PyType_Ready(&ps2con_type);
		PyType_Ready(&ButtonsIter_type);

		static struct PyModuleDef moduledef = {
			PyModuleDef_HEAD_INIT,
			"ps2con",
			"PS2 wireless controller driver",
			-1,
			module_methods,
			NULL,
			NULL,
			NULL,
			NULL
		};

		PyObject *pmodule = PyModule_Create(&moduledef);

		PyModule_AddIntMacro(pmodule, SELECT);
		PyModule_AddIntMacro(pmodule, L_HAT);
		PyModule_AddIntMacro(pmodule, R_HAT);
		PyModule_AddIntMacro(pmodule, START);
		PyModule_AddIntMacro(pmodule, DPAD_U);
		PyModule_AddIntMacro(pmodule, DPAD_R);
		PyModule_AddIntMacro(pmodule, DPAD_D);
		PyModule_AddIntMacro(pmodule, DPAD_L);
		PyModule_AddIntMacro(pmodule, L_TRIGGER);
		PyModule_AddIntMacro(pmodule, R_TRIGGER);
		PyModule_AddIntMacro(pmodule, L_SHOULDER);
		PyModule_AddIntMacro(pmodule, R_SHOULDER);
		PyModule_AddIntMacro(pmodule, TRIANGLE);
		PyModule_AddIntMacro(pmodule, CIRCLE);
		PyModule_AddIntMacro(pmodule, CROSS);
		PyModule_AddIntMacro(pmodule, SQUARE);
		PyModule_AddIntMacro(pmodule, LX);
		PyModule_AddIntMacro(pmodule, LY);
		PyModule_AddIntMacro(pmodule, RX);
		PyModule_AddIntMacro(pmodule, RY);

		return pmodule;
	}
}

