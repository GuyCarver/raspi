cmake_minimum_required (VERSION 2.8)
project(seeface)

#put this in for compile on raspi.
#SET(PIROOT /)
SET(CMAKE_MODULE_PATH ${PIROOT}usr/local/lib/cmake/)

include_directories(SYSTEM ${PIROOT}usr/local/include/ ${PIROOT}opt/vc/include/)
link_directories(${PIROOT}opt/vc/lib/)
find_package(raspicam REQUIRED)
find_package(OpenCV REQUIRED)

add_executable(seeface seeface.cpp)
target_link_libraries(seeface ${raspicam_LIBS} ${raspicam_CV_LIBS})

