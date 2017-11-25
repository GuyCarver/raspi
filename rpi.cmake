#Define out host system
SET(CMAKE_SYSTEM_NAME Linux)
SET(CMAKE_SYSTEM_VERSION 1)

SET(DEVROOT /home/gcarver/raspi/)
SET(PIROOT ${DEVROOT}rootfs/)
SET(PITOOLS ${DEVROOT}tools/)

SET(TOOLROOT ${PITOOLS}arm-bcm2708/arm-rpi-4.9.3-linux-gnueabihf/)

#Define the cross compiler locations
SET(CMAKE_C_COMPILER ${TOOLROOT}bin/arm-linux-gnueabihf-gcc)
SET(CMAKE_CXX_COMPILER ${TOOLROOT}bin/arm-linux-gnueabihf-g++)

#Can't put this in cuz it causes the gcc compiler test to fail.
#SET(CMAKE_SYSROOT ${PIROOT})
#SET(CMAKE_FIND_ROOT_PATH ${PIROOT})

#Define the sysroot path for the RaspberryPi distribution in our tools folder
#SET(CMAKE_FIND_ROOT_PATH /home/gcarver/raspi/tools/arm-bcm2708/arm-rpi-4.9.3-linux-gnueabihf/arm-linux-gnueabihf/sysroot/)
SET(CMAKE_MODULE_PATH ${PIROOT}usr/local/lib/cmake/)
SET(CMAKE_PREFIX_PATH ${PIROOT})

#python3 paths
#SET(PYTHON2_INCLUDE_PATH ${PIROOT}usr/include/python2.7/)
#SET(PYTHON2_LIBRARIES ${PIROOT}usr/lib/python2.7/)
#SET(PYTHON2_NUMPY_INCLUDE_DIRS ${PIROOT}usr/lib/python2.7/dist-packages/numpy/core/include/numpy/)
#SET(PYTHON3_INCLUDE_PATH ${PIROOT}usr/include/python3.5m/)
#SET(PYTHON3_LIBRARIES ${PIROOT}usr/lib/python3.5/)
#SET(PYTHON3_NUMPY_INCLUDE_DIRS ${PIROOT}usr/lib/python3/dist-packages/numpy/core/include/numpy/)

#Use our definitions for compiler tools
SET(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
#Search for libraries and headers in the target directories only
SET(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
SET(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)

SET(FLAGS "-Wl,-rpath-link,${PIROOT}opt/vc/lib -Wl,-rpath-link,${PIROOT}lib/arm-linux-gnueabihf -Wl,-rpath-link,${PIROOT}usr/lib/arm-linux-gnueabihf -Wl,-rpath-link,${PIROOT}usr/local/lib")

UNSET(CMAKE_C_FLAGS CACHE)
UNSET(CMAKE_CXX_FLAGS CACHE)

SET(CMAKE_CXX_FLAGS ${FLAGS} CACHE STRING "" FORCE)
SET(CMAKE_C_FLAGS ${FLAGS} CACHE STRING "" FORCE)

add_definitions(-Wall)
# -std=c11)

