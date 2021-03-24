 CC = g++

# compiler flags:
#  -g    adds debugging information to the executable file
#  -Wall turns on most, but not all, compiler warnings
CFLAGS  = -std=c++17 -O3 -fPIC

# the build target executable:
TARGET = mwick

lib: $(TARGET)lib

$(TARGET)lib: $(TARGET).cpp
	$(CC) $(CFLAGS) -shared -o $(TARGET)lib.so $(TARGET).cpp

exe: $(TARGET)

$(TARGET): $(TARGET).cpp
	$(CC) $(CFLAGS) -g -o $(TARGET) $(TARGET).cpp

clean:
	$(RM) $(TARGET)
