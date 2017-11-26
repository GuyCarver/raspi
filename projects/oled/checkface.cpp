//----------------------------------------------------------------------
// Copyright (c) 2017, Guy Carver
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
// FILE    checkface.cpp
// BY      Guy Carver
// DATE    11/22/2017 11:05 AM
//----------------------------------------------------------------------

#include <memory>
//#include <iostream>
#include <python3.5/Python.h>
#include <raspicam/raspicam_cv.h>
#include <opencv2/objdetect.hpp>
#include <opencv2/imgproc.hpp>

static PyObject *Create( PyObject *apSelf, PyObject *apArgs );
static PyObject *CheckFace( PyObject *apSelf, PyObject *apArg );
static PyObject *SetProp( PyObject *apSelf, PyObject *apArgs );
static PyObject *GetProp( PyObject *apSelf, PyObject *apArgs );
static PyObject *SetHorizontalFlip( PyObject *apSelf, PyObject *apArgs );
static PyObject *SetVerticalFlip( PyObject *apSelf, PyObject *apArgs );
//static PyObject *SetBrightness( PyObject *apSelf, PyObject *apArgs );
//static PyObject *SetContrast( PyObject *apSelf, PyObject *apArgs );
//static PyObject *SetSaturation( PyObject *apSelf, PyObject *apArgs );
//static PyObject *SetGain( PyObject *apSelf, PyObject *apArgs );
//static PyObject *SetExposure( PyObject *apSelf, PyObject *apArgs );

static const double DefaultScale = 0.25;

static PyMethodDef module_methods[] = {
	{"Create", Create, METH_VARARGS, "Create a CheckFaceCamera object and return it in a PyCapsules object."},
	{"Check", CheckFace, METH_O, "(CheckFaceCamera).\nTake a still from camera module with RaspiCam and detect faces using OpenCV."},
	{"SetProp", SetProp, METH_VARARGS, "(CheckFaceCamera, prop, value).\nSet CV_CAP_PROP_??? value."},
	{"GetProp", GetProp, METH_VARARGS, "Value (CheckFaceCamera, prop).\nGet CV_CAP_PROP_??? value."},
	{"SetHorizontalFlip", SetHorizontalFlip, METH_VARARGS, "(CheckFaceCamera, value).\nSet camera horizontal flip."},
	{"SetVerticalFlip", SetVerticalFlip, METH_VARARGS, "(CheckFaceCamera, value).\nSet camera vertical flip."},
//	{"SetBrightness", SetBrightness, METH_VARARGS, "(CheckFaceCamera, value).\nSet camera brightness."},
//	{"SetExposure", SetExposure, METH_VARARGS, "(CheckFaceCamera, value).\nSet camera exposure."},
//	{"SetGain", SetGain, METH_VARARGS, "(CheckFaceCamera, value).\nSet camera gain."},
//	{"SetSaturation", SetSaturation, METH_VARARGS, "(CheckFaceCamera, value).\nSet camera saturation."},
//	{"SetContrast", SetContrast, METH_VARARGS, "(CheckFaceCamera, value).\nSet camera contrast."},
	{NULL, NULL, 0, NULL}
};

extern "C" {
	PyMODINIT_FUNC PyInit_checkface(  )
	{
		static struct PyModuleDef moduledef = {
			PyModuleDef_HEAD_INIT,
			"checkface",
			"Raspberry Pi camera face detection.",
			-1,
			module_methods,
			NULL,
			NULL,
			NULL,
			NULL
		};

		PyObject *pmodule = PyModule_Create(&moduledef);

		PyModule_AddIntMacro(pmodule, CV_CAP_PROP_BRIGHTNESS);
		PyModule_AddIntMacro(pmodule, CV_CAP_PROP_CONTRAST);
		PyModule_AddIntMacro(pmodule, CV_CAP_PROP_SATURATION);
		PyModule_AddIntMacro(pmodule, CV_CAP_PROP_GAIN);
		PyModule_AddIntMacro(pmodule, CV_CAP_PROP_EXPOSURE);

		return pmodule;
	}
}

///
///<summary>  </summary>
///
class CheckFaceCamera
{
public:
	CheckFaceCamera(  )
	{
		try {
				// Change path before execution
//				HeadCascade.load("/usr/local/share/OpenCV/haarcascades/haarcascade_frontalcatface.xml");
				//This one is faster and more reliable that catface.
				HeadCascade.load("/usr/local/share/OpenCV/haarcascades/haarcascade_frontalface_default.xml");
		}
		catch(...) {
			PyErr_SetString(PyExc_RuntimeError, "Haarcascade setup error.");
		}
		try {
			//set camera params
			Camera.set(CV_CAP_PROP_FRAME_WIDTH, 640);
			Camera.set(CV_CAP_PROP_FRAME_HEIGHT, 480);
			Camera.set(CV_CAP_PROP_FORMAT, CV_8UC1);
			Camera.set(CV_CAP_PROP_EXPOSURE, -1);
//			Camera.set(CV_CAP_PROP_EXPOSURE, 50);
		}
		catch(...) {
			PyErr_SetString(PyExc_RuntimeError, "Camera Init error.");
		}
		try {
			bOk = Camera.open();
		}
		catch(...) {
			PyErr_SetString(PyExc_RuntimeError, "Camera Open error.");
		}
	}

	~CheckFaceCamera()
	{
		try {
			Camera.release();
		}
		catch(...) {
			PyErr_SetString(PyExc_RuntimeError, "Camera Release error.");
		}
	}

	static void Kill( PyObject *apArg )
	{
		auto pcheck = reinterpret_cast<CheckFaceCamera*>(PyCapsule_GetPointer(apArg, CheckFaceCamera::Name));
		delete pcheck;
	}

	bool CheckFace(  )
	{
		bool bres = true;
		if (QOk()) {
			cv::Mat image;

			try {
				Camera.grab();
				Camera.retrieve(image);
			}
			catch(...) {
				PyErr_SetString(PyExc_RuntimeError, "Camera frame grab error.");
			}

			cv::Mat smallImg;

			try {
				cv::resize(image, smallImg, cv::Size(), DefaultScale, DefaultScale, cv::INTER_LINEAR);
//				cv::equalizeHist(smallImg, smallImg);
			}
			catch(...) {
				PyErr_SetString(PyExc_RuntimeError, "opencv image resize error.");
			}

			std::vector<cv::Rect> faces;
			HeadCascade.detectMultiScale(smallImg, faces, 1.1, 2, cv::CASCADE_SCALE_IMAGE, cv::Size(30, 30));
			bres = (faces.size() != 0);
		}
		return bres;
	}

	bool QOk(  ) const { return bOk; }

	static const char *Name;

	void set( int32_t aPropID, double aValue )
	{
		Camera.set(aPropID, aValue);
	}

	double get( int32_t aPropID )
	{
		return Camera.get(aPropID);
	}

	void setHorizontalFlip( bool aValue )
	{
		Camera.setHorizontalFlip(aValue);
	}

	void setVerticalFlip( bool aValue )
	{
		Camera.setVerticalFlip(aValue);
	}

private:
	raspicam::RaspiCam_Cv Camera;
	cv::CascadeClassifier HeadCascade;
	bool bOk = false;
};

const char *CheckFaceCamera::Name = "CheckFaceCamera";

///
///<summary>  </summary>
///
static PyObject *Create( PyObject */*apSelf*/, PyObject */*apArgs*/ )
{
	auto pcheck = new CheckFaceCamera();
	//Wrap our camera in a PyCapsule.  When PyCapsule is deleted Kill() will be called.
	PyObject *pret = PyCapsule_New(pcheck, CheckFaceCamera::Name, CheckFaceCamera::Kill);
	return pret;
}

static PyObject *CheckFace( PyObject *apSelf , PyObject *apArg )
{
	auto pcheck = reinterpret_cast<CheckFaceCamera*>(PyCapsule_GetPointer(apArg, CheckFaceCamera::Name));
	bool bres = pcheck ? pcheck->CheckFace() : true;
	return PyBool_FromLong(bres);
}

//Clamp a value between min and max.
template<typename T> T clamp( T aValue, T aMin, T aMax )
{
	return std::min(aMax, std::max(aMin, aValue));
}

static PyObject *SetProp( PyObject *apSelf , PyObject *apArgs )
{
	PyObject *pobj;
	int32_t prop;
	double value;
	if (!PyArg_ParseTuple(apArgs, "Oid", &pobj, &prop, &value))
		PyErr_SetString(PyExc_RuntimeError, "Incorrect params.  Expect Object, int, float.");

	auto pcheck = reinterpret_cast<CheckFaceCamera*>(PyCapsule_GetPointer(pobj, CheckFaceCamera::Name));
	if (pcheck) {
		pcheck->set(prop, value);
	}

	Py_RETURN_NONE;
}

static PyObject *GetProp( PyObject *apSelf , PyObject *apArgs )
{
	PyObject *pobj;
	int32_t prop;
	if (!PyArg_ParseTuple(apArgs, "Oi", &pobj, &prop))
		PyErr_SetString(PyExc_RuntimeError, "Incorrect params.  Expect Object, int, float.");

	auto pcheck = reinterpret_cast<CheckFaceCamera*>(PyCapsule_GetPointer(pobj, CheckFaceCamera::Name));
	double value = 0.0;
	if (pcheck) {
		value = pcheck->get(prop);
	}

	return Py_BuildValue("d", value);
}

static PyObject *SetHorizontalFlip( PyObject *apSelf , PyObject *apArgs )
{
	PyObject *pobj;
	bool value;
	if (!PyArg_ParseTuple(apArgs, "Ob", &pobj, &value))
		PyErr_SetString(PyExc_RuntimeError, "Incorrect params.  Expect Object, True/False.");

	auto pcheck = reinterpret_cast<CheckFaceCamera*>(PyCapsule_GetPointer(pobj, CheckFaceCamera::Name));
	if (pcheck) {
		pcheck->setHorizontalFlip(value);
	}

	Py_RETURN_NONE;
}

static PyObject *SetVerticalFlip( PyObject *apSelf , PyObject *apArgs )
{
	PyObject *pobj;
	bool value;
	if (!PyArg_ParseTuple(apArgs, "Ob", &pobj, &value))
		PyErr_SetString(PyExc_RuntimeError, "Incorrect params.  Expect Object, True/False");

	auto pcheck = reinterpret_cast<CheckFaceCamera*>(PyCapsule_GetPointer(pobj, CheckFaceCamera::Name));
	if (pcheck) {
		pcheck->setVerticalFlip(value);
	}

	Py_RETURN_NONE;
}


//static PyObject *SetContrast( PyObject *apSelf , PyObject *apArgs )
//{
//	PyObject *pobj;
//	double value;
//	if (!PyArg_ParseTuple(apArgs, "Od", &pobj, &value))
//		PyErr_SetString(PyExc_RuntimeError, "Incorrect params.  Expect Object, float.");
//
//	auto pcheck = reinterpret_cast<CheckFaceCamera*>(PyCapsule_GetPointer(pobj, CheckFaceCamera::Name));
//	if (pcheck) {
//		value = clamp(value, 0.0, 100.0);
//		pcheck->set(CV_CAP_PROP_CONTRAST, value);
//	}
//
//	Py_RETURN_NONE;
//}
//
//static PyObject *SetBrightness( PyObject *apSelf , PyObject *apArgs )
//{
//	PyObject *pobj;
//	double value;
//	if (!PyArg_ParseTuple(apArgs, "Od", &pobj, &value))
//		PyErr_SetString(PyExc_RuntimeError, "Incorrect params.  Expect Object, float.");
//
//	auto pcheck = reinterpret_cast<CheckFaceCamera*>(PyCapsule_GetPointer(pobj, CheckFaceCamera::Name));
//	if (pcheck) {
//		value = clamp(value, 0.0, 100.0);
//		pcheck->set(CV_CAP_PROP_BRIGHTNESS, value);
//	}
//
//	Py_RETURN_NONE;
//}
//
//static PyObject *SetSaturation( PyObject *apSelf , PyObject *apArgs )
//{
//	PyObject *pobj;
//	double value;
//	if (!PyArg_ParseTuple(apArgs, "Od", &pobj, &value))
//		PyErr_SetString(PyExc_RuntimeError, "Incorrect params.  Expect Object, float.");
//
//	auto pcheck = reinterpret_cast<CheckFaceCamera*>(PyCapsule_GetPointer(pobj, CheckFaceCamera::Name));
//	if (pcheck) {
//		value = clamp(value, 0.0, 100.0);
//		pcheck->set(CV_CAP_PROP_SATURATION, value);
//	}
//
//	Py_RETURN_NONE;
//}
//
//static PyObject *SetGain( PyObject *apSelf , PyObject *apArgs )
//{
//	PyObject *pobj;
//	double value;
//	if (!PyArg_ParseTuple(apArgs, "Od", &pobj, &value))
//		PyErr_SetString(PyExc_RuntimeError, "Incorrect params.  Expect Object, float.");
//
//	auto pcheck = reinterpret_cast<CheckFaceCamera*>(PyCapsule_GetPointer(pobj, CheckFaceCamera::Name));
//	if (pcheck) {
//		value = clamp(value, 0.0, 100.0);
//		pcheck->set(CV_CAP_PROP_GAIN, value);
//	}
//
//	Py_RETURN_NONE;
//}
//
//static PyObject *SetExposure( PyObject *apSelf , PyObject *apArgs )
//{
//	PyObject *pobj;
//	double value;
//	if (!PyArg_ParseTuple(apArgs, "Od", &pobj, &value))
//		PyErr_SetString(PyExc_RuntimeError, "Incorrect params.  Expect Object, float.");
//
//	auto pcheck = reinterpret_cast<CheckFaceCamera*>(PyCapsule_GetPointer(pobj, CheckFaceCamera::Name));
//	if (pcheck) {
//		value = clamp(value, -1.0, 100.0);
//		pcheck->set(CV_CAP_PROP_EXPOSURE, value);
//	}
//
//	Py_RETURN_NONE;
//}
