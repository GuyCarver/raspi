 CC = g++

# compiler flags:
#  -g    adds debugging information to the executable file
#  -Wall turns on most, but not all, compiler warnings
LFLAGS  = -lwiringPi
CFLAGS  = -Wall -c -std=c++17 -fPIC -O3

# the build target executable:
TARGET = vl53lib

OBJ = $(TARGET).o

%.o: %.cpp
	$(CC) $(CFLAGS) -o $@ $<

lib: $(OBJ)
	$(CC) $(LFLAGS) -shared -o $(TARGET).so $^

exe: $(OBJ)
	$(CC) $(LFLAGS) -g -o $(TARGET) $^

clean:
	$(RM) $(OBJ)

cleanall: clean
	$(RM) $(TARGET).so

