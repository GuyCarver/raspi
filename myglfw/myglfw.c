//Test program for glfw use.

#include <GL/glfw.h>

void ShutDown( int uiReturnCode )
{
	glfwTerminate();
	exit(uiReturnCode);
}

int main( int argc, char **argv )
{
	if (glfwOpenWindow(640, 480, 5, 6, 5, 0, 8, 0, GLFW_FULLSCREEN) != GL_TRUE)
		ShutDown(1);

	glfwSetWindowTitle("My GLFW Window");

	bool bquit = false;

	while(!bquit)
	{
		glfwPollEvents();
		bquit = (glfwGetKey(GLFW_KEY_ESC) == GLFW_PRESS);
	}
}
