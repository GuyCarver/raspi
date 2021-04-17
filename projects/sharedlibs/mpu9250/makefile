 CC = g++

# compiler flags:
#  -g    adds debugging information to the executable file
#  -Wall turns on most, but not all, compiler warnings
CFLAGS  = -std=c++17 -O3 -fPIC
INCLUDE = -I "/usr/include/" -I "/usr/local/include/"
OBJ = mpu9250.o matrix3.o

# the build target executable:
TARGET = mpu9250

%.o: %.cpp
	$(CC) -c -o $@ $< $(CFLAGS)

lib: $(OBJ)
	$(CC) $(CFLAGS) -lwiringPi  -shared -o $(TARGET)lib.so $^

m3: matrix3.cpp
	$(CC) $(CFLAGS) -shared -o m3lib.so $<

clean:
	$(RM) $(TARGET)
