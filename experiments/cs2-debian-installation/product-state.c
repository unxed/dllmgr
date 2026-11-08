#include <windows.h>
#include <msi.h>
#include <stdio.h>
int main(void) {
 const char *product="{236BB7C4-4419-42FD-0409-1E257A25E34D}";
 char version[128]={0},name[256]={0}; DWORD vs=sizeof(version),ns=sizeof(name);
 INSTALLSTATE state=MsiQueryProductStateA(product);
 UINT vr=MsiGetProductInfoA(product,INSTALLPROPERTY_VERSIONSTRING,version,&vs);
 UINT nr=MsiGetProductInfoA(product,INSTALLPROPERTY_INSTALLEDPRODUCTNAME,name,&ns);
 printf("product=%s state=%d version_status=%u version=%s name_status=%u name=%s\n",product,state,vr,version,nr,name);
 return state==INSTALLSTATE_DEFAULT?0:1;
}
