//#include <iostream>

#ifdef UNICODE
#define ReadConsole ReadConsoleW
#else
#define ReadConsole ReadConsoleA
#endif

void ReadConsoleW();