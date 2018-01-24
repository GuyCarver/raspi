
// Include required header files from OpenCV directory
#include <time.h>
//#include <raspicam/raspicam_still_cv.h>
#include <raspicam/raspicam_cv.h>
#include <opencv2/objdetect.hpp>
#include <opencv2/imgproc.hpp>
//#include <opencv2/opencv.hpp>
#include <iostream>

// Function for Face Detection

void detectAndDraw( cv::Mat &img, cv::CascadeClassifier &cascade, cv::CascadeClassifier &nestedCascade, double scale )
{
	std::vector<cv::Rect> faces;
	cv::Mat grayImg;
	cv::Mat smallImg;

	cv::resize(img, smallImg, cv::Size(), scale, scale, cv::INTER_LINEAR);
	cv::cvtColor(smallImg, grayImg, cv::COLOR_BGR2GRAY); // Convert to Gray Scale

//	grayImg = smallImg.clone();
//	double radius = 0.0;

//	grayImg.convertTo(grayImg, CV_8UC1);
	// Resize the Grayscale Image
//	std::cout << "grayImg Fmt = " << grayImg.type() << std::endl;;
//	std::cout << "equalizing." << std::endl;
	cv::equalizeHist(grayImg, grayImg);
//	std::cout << "Looking for face." << std::endl;

	// Detect faces of different sizes using cascade classifier
	cascade.detectMultiScale(grayImg, faces, 1.1, 2, 0|cv::CASCADE_SCALE_IMAGE, cv::Size(30, 30));

	// Draw circles around the faces
	for ( size_t i = 0; i < faces.size(); i++ ) {
		cv::Rect r = faces[i];
//		radius = (r.width + r.height) * 0.25 * scale;

		cv::Point center;
		const cv::Scalar color = cv::Scalar(255, 0, 0); // Color for Drawing tool
		const cv::Scalar color2 = cv::Scalar(0, 255, 0);
		int radius;
//
		double aspect_ratio = (double)r.width/r.height;
		if( 0.75 < aspect_ratio && aspect_ratio < 1.3 )
		{
			center.x = cvRound((r.x + r.width*0.5));
			center.y = cvRound((r.y + r.height*0.5));
			radius = cvRound((r.width + r.height)*0.25);
			cv::circle( grayImg, center, radius, color, 1, 8, 0 );
		}
		else
			cv::rectangle( grayImg, cvPoint(cvRound(r.x), cvRound(r.y)),
					cvPoint(cvRound((r.x + r.width-1)),
					cvRound((r.y + r.height-1))), color, 1, 8, 0);

//		if (nestedCascade.empty()) {
//			continue;
//		}

		std::cout << "Found face size: " << r.width << ", " << r.height << std::endl;
/*		cv::Mat smallImgROI = grayImg(r);

		std::cout << "  looking for eyes" << std::endl;

		// Detection of eyes int the input image
		std::vector<cv::Rect> nestedObjects;
		nestedCascade.detectMultiScale(smallImgROI, nestedObjects, 1.1, 2, 0|cv::CASCADE_SCALE_IMAGE, cv::Size(30, 30));

		if (nestedObjects.size() > 0) {
			std::cout << "  found eyes: " << nestedObjects.size() << std::endl;
		}

		// Draw circles around eyes
		for ( size_t j = 0; j < nestedObjects.size(); j++ ) {

			cv::Rect nr = nestedObjects[j];
			center.x = cvRound((r.x + nr.x + nr.width*0.5));
			center.y = cvRound((r.y + nr.y + nr.height*0.5));
			radius = (nr.width + nr.height) * 0.25;
			std::cout << "    Found eyes size: " << radius << std::endl;
			circle( grayImg, center, radius, color2, 1, 8, 0 );
		}
*/
		// Show Processed Image with detected faces
	}
	cv::imshow( "Face Detection", grayImg );
}

int main( int argc, const char **argv )
{
	cv::Mat frame;

	std::cout << "CV_8UC1 = " << CV_8UC1 << std::endl;

	//set camera params
	raspicam::RaspiCam_Cv Camera;
	Camera.set(CV_CAP_PROP_FORMAT, CV_8UC4);
	Camera.set(CV_CAP_PROP_FRAME_WIDTH, 640);
	Camera.set(CV_CAP_PROP_FRAME_HEIGHT, 480);
	Camera.set(CV_CAP_PROP_EXPOSURE, -1);
	Camera.set(CV_CAP_PROP_CONTRAST, 100.0);
	Camera.set(CV_CAP_PROP_SATURATION, 100.0);
	Camera.set(CV_CAP_PROP_BRIGHTNESS, 50.0);
	Camera.set(CV_CAP_PROP_GAIN, 65.0);
	Camera.setVerticalFlip(false);
	double scale = 0.5;

	if (!Camera.open()) {
		std::cerr << "Error opening the camera" << std::endl;
//		return -1;
	}

	// PreDefined trained XML classifiers with facial features
	cv::CascadeClassifier cascade, nestedCascade;

	// Load classifiers from "opencv/data/haarcascades" directory
//	nestedCascade.load( "/usr/local/share/OpenCV/haarcascades/haarcascade_eye_tree_eyeglasses.xml" ) ;

	// Change path before execution
	cascade.load( "/usr/local/share/OpenCV/haarcascades/haarcascade_frontalface_default.xml" ) ;

	// Capture frames from video and detect faces
	std::cout << "Face Detection Started...." << std::endl;
	struct timespec ts;

	cv::namedWindow("Face Detection", cv::WINDOW_AUTOSIZE);

	unsigned int prop = CV_CAP_PROP_BRIGHTNESS;
	const char *propname = "brightness";

	while(1) {
		cv::Mat frame;
		Camera.grab();
		Camera.retrieve(frame);

		if (frame.empty()) {
			break;
		}

		cv::Mat frame1 = frame.clone();
		detectAndDraw(frame1, cascade, nestedCascade, scale);

		char c = (char)cv::waitKey(10);

		// Press q to exit from window
		if ((c == 27) || (c == 'q') || (c == 'Q')) {
			break;
		}

		double v = 0.0;
		switch (c) {
			case 'e':
				prop = CV_CAP_PROP_EXPOSURE;
				propname = "exposure";
				break;
			case 'b':
				prop = CV_CAP_PROP_BRIGHTNESS;
				propname = "brightness";
				break;
			case 'g':
				prop = CV_CAP_PROP_GAIN;
				propname = "gain";
				break;
			case 's':
				prop = CV_CAP_PROP_SATURATION;
				propname = "saturation";
				break;
			case 'c':
				prop = CV_CAP_PROP_CONTRAST;
				propname = "contrast";
				break;
			case 'p':
				scale = 0.125;
				break;
			case '[':
				scale = 0.25;
				break;
			case ']':
				scale = 0.5;
				break;
			case '1':
				v = 10.0;
				break;
			case '2':
				v = 20.0;
				break;
			case '3':
				v = 30.0;
				break;
			case '4':
				v = 40.0;
				break;
			case '5':
				v = 50.0;
				break;
			case '6':
				v = 60.0;
				break;
			case '7':
				v = 70.0;
				break;
			case '8':
				v = 80.0;
				break;
			case '9':
				v = 90.0;
				break;
			case '!':
				v = 15.0;
				break;
			case '@':
				v = 25.0;
				break;
			case '#':
				v = 35.0;
				break;
			case '$':
				v = 45.0;
				break;
			case '%':
				v = 55.0;
				break;
			case '^':
				v = 65.0;
				break;
			case '&':
				v = 75.0;
				break;
			case '*':
				v = 85.0;
				break;
			case '(':
				v = 95.0;
				break;
			case '0':
				v = 100.0;
				break;
			case ')':
				if (prop == CV_CAP_PROP_EXPOSURE) {
					v = -1.0;
				}
				break;
			default:
				break;
		}

		if (v > 0.0) {
			std::cout << "Setting " << propname << " to " << v << std::endl;
			Camera.set(prop, v);
		}

		ts.tv_sec = 10 / 1000;
		ts.tv_nsec = (10 % 1000) * 1000000;
		nanosleep(&ts, NULL);
	}

	Camera.release();
	return 0;
}

//#include <ctime>
//#include <iostream>
//#include <raspicam/raspicam_cv.h>
//using namespace std;
//
//int main( int argc, char **argv ) {
//	time_t timer_begin,timer_end;
//	raspicam::RaspiCam_Cv Camera;
//	cv::Mat image;
//	int nCount = 100;
//
//	//set camera params
//	Camera.set(CV_CAP_PROP_FORMAT, CV_8UC1);
//
//	//Open camera
//	cout << "Opening Camera..." << endl;
//	if (!Camera.open()) {
//		cerr << "Error opening the camera" << endl;
//		return -1;
//	}
//	//Start capture
//	cout << "Capturing " << nCount << " frames ...." << endl;
//	time(&timer_begin);
//	for ( int i = 0; i < nCount; i++ ) {
//		Camera.grab();
//		Camera.retrieve(image);
//		if ((i % 5) == 0) {
//			cout << "\r captured " << i << " images" << std::flush;
//		}
//	}
//	cout << "Stop camera..." << endl;
//	Camera.release();
//
//	//show time statistics
//	time(&timer_end); /* get current time; same as: timer = time(NULL)  */
//	double secondsElapsed = difftime(timer_end, timer_begin);
//	cout << secondsElapsed << " seconds for " << nCount << "  frames : FPS = " << (float)nCount / (float)secondsElapsed << endl;
//	//save image
//	cv::imwrite("raspicam_cv_image.jpg", image);
//	cout << "Image saved at raspicam_cv_image.jpg" << endl;
//}

// CPP program to detects face in a video

