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
#include <Python.h>
#include <iostream>
#include <raspicam/raspicam_cv.h>
#include <opencv2/objdetect.hpp>
#include <opencv2/imgproc.hpp>

static const char module_docstring[] = "Raspberry Pi camera face detection.";
static const char create_docstring[] = "Return CheckFaceCamera object.\nCreate a seeface object and return it in a PyCapsules object.";
static const char checkface_docstring[] = "Pass CheckFaceCamera object.\nTake a still from camera module with RaspiCam and detect faces using OpenCV.";

static PyObject *Create( PyObject *apSelf, PyObject *apArgs );
static PyObject *CheckFace( PyObject *apSelf, PyObject *apArg );

extern "C" {
	static PyMethodDef module_methods[] = {
		{"Create", Create, METH_VARARGS, create_docstring},
		{"CheckFace", CheckFace, METH_O, checkface_docstring},
		{NULL, NULL, 0, NULL}
	};

	PyMODINIT_FUNC PyInit__checkface(  )
	{
		static struct PyModuleDef moduledef = {
			PyModuleDef_HEAD_INIT,
			"checkface",
			module_docstring,
			-1,
			module_methods,
			NULL,
			NULL,
			NULL,
			NULL
		};

		PyObject *pmodule = PyModule_Create(&moduledef);

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
		// Load classifiers from "opencv/data/haarcascades" directory
		EyeCascade.load("/usr/local/share/OpenCV/haarcascades/haarcascade_eye_tree_eyeglasses.xml");

		// Change path before execution
		HeadCascade.load("/usr/local/share/OpenCV/haarcascades/haarcascade_frontalcatface.xml");

		//set camera params
		Camera.set(CV_CAP_PROP_FRAME_WIDTH, 640);
		Camera.set(CV_CAP_PROP_FRAME_HEIGHT, 480);
		Camera.set(CV_CAP_PROP_FORMAT, CV_8UC1);
		Camera.set(CV_CAP_PROP_EXPOSURE, 50);
		bOk = Camera.open();
	}

	~CheckFaceCamera()
	{
		Camera.release();
	}

	static void Kill( PyObject *apArg )
	{
		auto pcheck = reinterpret_cast<CheckFaceCamera*>(PyCapsule_GetPointer(apArg, CheckFaceCamera::Name));
		delete pcheck;
	}

	bool CheckFace(  ) const
	{
		bool bres = false;
		if (QOk()) {
			cv::Mat image;

			Camera.grab();
			Camera.retrieve(image);

			cv::Mat smallImg;
			cv::resize(image, smallImg, cv::Size(), 0.5, 0.5, cv::INTER_LINEAR);
			cv::equalizeHist(smallImg, smallImg);

			std::vector<cv::Rect> faces;
			HeadCascade.detectMultiScale(smallImg, faces, 1.1, 2, cv::CASCADE_SCALE_IMAGE, cv::Size(30, 30));

			if (faces.size()) {
				//TODO: Check for eyes.
				bres = true;
			}
		}
		return bres;
	}

	bool QOk(  ) const { return bOk; }

	static const char *Name;

private:
	raspicam::RaspiCam_Cv Camera;
	cv::CascadeClassifier EyeCascade;
	cv::CascadeClassifier HeadCascade;
	bool bOk = false;
};

const char *CheckFaceCamera::Name = "CheckFaceCamera";

///
///<summary>  </summary>
///
static PyObject *Create( PyObject */*apSelf*/, PyObject */*apArgs*/ )
{
//	double m, b;
//	PyObject *x_obj, *y_obj, *yerr_obj;
//	if (!PyArg_ParseTuple(args, "ddOOO", &m, &b, &x_obj, &y_obj, &yerr_obj))
//		return nullptr;

	auto pcheck = new CheckFaceCamera();
	//Wrap our camera in a PyCapsule.  When PyCapsule is deleted Kill() will be called.
	PyObject *pret = PyCapsule_New(pcheck, CheckFaceCamera::Name, CheckFaceCamera::Kill);
	return pret;
}

static PyObject *CheckFace( PyObject *apSelf , PyObject *apArg )
{
	auto pcheck = reinterpret_cast<checkface*>(PyCapsule_GetPointer(apArg, Name));
	bool bres = pcheck ? pcheck->CheckFace() : false;
	return PyBool_FromLong(bres);
}

