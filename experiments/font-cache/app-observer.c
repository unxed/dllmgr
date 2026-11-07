#define main general_observer_main
#include "app-observer.c"
#undef main
int main(int argc,char **argv)
{
 STARTUPINFOW startup={sizeof(startup)};PROCESS_INFORMATION process;WCHAR command[4096],**args;
 HWND window,draw;DWORD start;int n,status=0;
 if(argc!=3)return 2;
 SetProcessDPIAware();setvbuf(stdout,NULL,_IONBF,0);
 args=CommandLineToArgvW(GetCommandLineW(),&n);if(!args || n!=3)return 2;
 if(wcslen(args[1])+wcslen(args[2])+6>=ARRAYSIZE(command))return 2;
 swprintf(command,ARRAYSIZE(command),L"\"%ls\" \"%ls\"",args[1],args[2]);LocalFree(args);
 start=GetTickCount();if(!CreateProcessW(NULL,command,NULL,NULL,FALSE,0,NULL,NULL,&startup,&process))return 3;
 pid=process.dwProcessId;app_process=process.hProcess;
 window=wait_window(NULL,NULL);report_timing("startup",start,window);
 if(!window)status=4;
 else {
  Sleep(1000);
  if(!activate_owned_window(window))status=7;
  else {
   start=GetTickCount();press_key('D');draw=wait_window("Draw Board","TDrawBoard");report_timing("draw",start,draw);
   if(!draw)status=5;
   else {puts("draw_ready_sample_memory");Sleep(1500);}
  }
 }
 TerminateProcess(process.hProcess,status);WaitForSingleObject(process.hProcess,5000);
 CloseHandle(process.hThread);CloseHandle(process.hProcess);return status;
}
