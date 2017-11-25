#include <ctime>
#include <iostream>
#include <raspicam/raspicam_cv.h>
#include <opencv2/objdetect.hpp>
#include <opencv2/imgproc.hpp>
using namespace std;

int main ( int argc, char **argv )
{
	time_t timer_begin, timer_end;
	raspicam::RaspiCam_Cv Camera;
	cv::Mat image;

	int nCount = 100;

	cv::CascadeClassifier cascade, nestedCascade;
	double scale = 1;

	// Load classifiers from "opencv/data/haarcascades" directory
	nestedCascade.load("/usr/local/share/OpenCV/haarcascades/haarcascade_eye_tree_eyeglasses.xml");

	// Change path before execution
	cascade.load("/usr/local/share/OpenCV/haarcascades/haarcascade_frontalcatface.xml");

	//set camera params
	Camera.set(CV_CAP_PROP_FRAME_WIDTH, 640);
	Camera.set(CV_CAP_PROP_FRAME_HEIGHT, 480);
	Camera.set(CV_CAP_PROP_FORMAT, CV_8UC1);
	Camera.set(CV_CAP_PROP_EXPOSURE, 50);

	//Open camera
	cout << "Opening Camera..." << endl;
	if (!Camera.open()) {
		cerr << "Error opening the camera" << endl;
		return -1;
	}
	//Start capture
	cout << "Capturing " << nCount << " frames ...." << endl;
	time(&timer_begin);
	cv::namedWindow("Face Image", cv::WINDOW_AUTOSIZE);

	for ( int i = 0; i < nCount; i++ ) {
		std::vector<cv::Rect> faces;
		cout << "Capturing: " << i << endl;
		Camera.grab();
		Camera.retrieve(image);

		cv::Mat smallImg;
		cv::resize(image, smallImg, cv::Size(), 0.5, 0.5, cv::INTER_LINEAR);
		cv::equalizeHist(smallImg, smallImg);

		cascade.detectMultiScale(smallImg, faces, 1.1, 2, 0|cv::CASCADE_SCALE_IMAGE, cv::Size(30, 30));

		if (faces.size()) {
			cout << "found " << faces.size() << " faces." << endl;
		}

		imshow("Face Image", smallImg);

//		if (i % 5 == 0)  {
//			cout << "\r captured " << i << " images" << std::flush;
//		}
	}
	cout << "Stop camera..." << endl;
	Camera.release();

	//show time statistics
	time(&timer_end); /* get current time; same as: timer = time(NULL)  */
	double secondsElapsed = difftime(timer_end,timer_begin);
	cout << secondsElapsed << " seconds for " << nCount << "  frames : FPS = " << (float)((float)(nCount) / secondsElapsed) << endl;
	//save image
//	cv::imwrite("raspicam_cv_image.jpg", image);
//	cout << "Image saved at raspicam_cv_image.jpg" << endl;
}

