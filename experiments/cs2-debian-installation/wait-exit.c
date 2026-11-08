#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
int main(int argc,char **argv) {
 HANDLE handles[16]={0}; DWORD ids[16]={0}; int count=argc-1; if(count>16)count=16;
 for(int i=0;i<count;i++) { ids[i]=strtoul(argv[i+1],NULL,0);handles[i]=OpenProcess(SYNCHRONIZE|PROCESS_QUERY_LIMITED_INFORMATION,FALSE,ids[i]);printf("opened pid=%lu handle=%p error=%lu\n",ids[i],handles[i],handles[i]?0:GetLastError());fflush(stdout); }
 for(int i=0;i<count;i++) if(handles[i]) {DWORD rc=WaitForSingleObject(handles[i],600000),exit=STILL_ACTIVE;GetExitCodeProcess(handles[i],&exit);printf("exited pid=%lu wait=%lu code=%lu hex=%08lx\n",ids[i],rc,exit,exit);fflush(stdout);CloseHandle(handles[i]);}
 return 0;
}
