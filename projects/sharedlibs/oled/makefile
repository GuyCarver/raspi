 CC = g++

# compiler flags:
#  -g    adds debugging information to the executable file
#  -Wall turns on most, but not all, compiler warnings
CFLAGS = -Wall -c -std=c++17 -fPIC -O3

# the build target executable:
TARGET = oledlib

OBJ = $(TARGET).o

%.o: %.cpp
	$(CC) $(CFLAGS) -o $@ $<

lib: $(OBJ)
	$(CC) -shared -o $(TARGET).so $^

exe: $(OBJ)
	$(CC) -lpthread -g -o $(TARGET) $^

clean:
	$(RM) $(OBJ)

cleanall: clean
	$(RM) $(TARGET).so

