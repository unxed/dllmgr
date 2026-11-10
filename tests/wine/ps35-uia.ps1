# Public Windows APIs and UI Automation only. Loaded by ps35-windows.ps1.
Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes,System.Drawing,System.Windows.Forms
Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;
namespace PS35 {
 public class Window {
  public long Handle; public uint ProcessId; public string Text,ClassName;
  public int X,Y,Width,Height,ClientWidth,ClientHeight; public uint Dpi;
 }
 public static class Native {
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L,T,R,B; }
  delegate bool EnumProc(IntPtr h,IntPtr p);
  [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc c,IntPtr p);
  [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr h,StringBuilder s,int n);
  [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern int GetClassName(IntPtr h,StringBuilder s,int n);
  [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h,out uint p);
  [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr h,out RECT r);
  [DllImport("user32.dll")] static extern bool GetClientRect(IntPtr h,out RECT r);
  [DllImport("user32.dll")] public static extern uint GetDpiForWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern uint GetDpiForSystem();
  [DllImport("msi.dll",CharSet=CharSet.Unicode)] public static extern int MsiQueryProductState(string product);
  [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h,uint m,IntPtr w,IntPtr l);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool IsWindowEnabled(IntPtr h);
  [DllImport("user32.dll")] static extern bool SetCursorPos(int x,int y);
  [DllImport("user32.dll")] static extern void mouse_event(uint f,uint x,uint y,uint d,UIntPtr e);
  // A real click at a point UIA reported for the element (its clickable point).
  public static void Click(int x,int y) { SetCursorPos(x,y);mouse_event(2,0,0,0,UIntPtr.Zero);mouse_event(4,0,0,0,UIntPtr.Zero); }
  [DllImport("user32.dll")] static extern void keybd_event(byte vk,byte scan,uint f,UIntPtr e);
  // #47: Alt (VK_MENU) held, one wheel notch at a point
  public static void AltWheel(int x,int y,int delta,bool press,bool release) {
   SetCursorPos(x,y); if(press) keybd_event(0x12,0x38,0,UIntPtr.Zero);
   mouse_event(0x0800,0,0,(uint)delta,UIntPtr.Zero); if(release) keybd_event(0x12,0x38,2,UIntPtr.Zero);
  }
  [DllImport("user32.dll",EntryPoint="SendMessageTimeoutW",CharSet=CharSet.Unicode,SetLastError=true)]
  static extern IntPtr SendText(IntPtr h,uint m,IntPtr w,string text,uint flags,uint timeout,out IntPtr result);
  public static bool SetText(IntPtr h,string text) {
   IntPtr result;return SendText(h,0xC,IntPtr.Zero,text,2,5000,out result)!=IntPtr.Zero && result!=IntPtr.Zero;
  }
  public static Window[] Windows() {
   var a=new List<Window>();
   EnumWindows((h,p)=>{
    if(!IsWindowVisible(h))return true;
    var s=new StringBuilder(1024);var c=new StringBuilder(128);uint id;RECT r,cr;
    GetWindowText(h,s,s.Capacity);GetClassName(h,c,c.Capacity);GetWindowThreadProcessId(h,out id);
    GetWindowRect(h,out r);GetClientRect(h,out cr);
    a.Add(new Window{Handle=h.ToInt64(),ProcessId=id,Text=s.ToString(),ClassName=c.ToString(),X=r.L,Y=r.T,Width=r.R-r.L,Height=r.B-r.T,ClientWidth=cr.R-cr.L,ClientHeight=cr.B-cr.T,Dpi=GetDpiForWindow(h)});return true;
   },IntPtr.Zero);return a.ToArray();
  }
 }
}
'@
function Save-Desktop([string]$Name){
    $Bounds=[System.Windows.Forms.SystemInformation]::VirtualScreen
    $Bitmap=New-Object System.Drawing.Bitmap $Bounds.Width,$Bounds.Height
    $G=[System.Drawing.Graphics]::FromImage($Bitmap)
    try{$G.CopyFromScreen($Bounds.Location,[System.Drawing.Point]::Empty,$Bounds.Size);$Bitmap.Save((Join-Path $Out "$Name.png"))}finally{$G.Dispose();$Bitmap.Dispose()}
}
function Save-UiTree([System.Windows.Automation.AutomationElement]$Root,[string]$Name){
    $Rows=@();$Elements=$Root.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition)
    for($i=0;$i -lt [Math]::Min($Elements.Count,1200);$i++){
        try{$C=$Elements[$i].Current;$Rows+=@{name=$C.Name;type=$C.ControlType.ProgrammaticName;class=$C.ClassName;handle=$C.NativeWindowHandle;enabled=$C.IsEnabled;offscreen=$C.IsOffscreen;automation_id=$C.AutomationId;patterns=@($Elements[$i].GetSupportedPatterns() | ForEach-Object {$_.ProgrammaticName})}}catch{}
    }
    ConvertTo-Json -InputObject $Rows -Depth 5 | Set-Content (Join-Path $Out "$Name-uia.json")
}
function Normalize-UiName([string]$Name){return (($Name -replace '\t.*$','') -replace '[^a-zA-Z0-9]','').ToLowerInvariant()}
function Find-Named([System.Windows.Automation.AutomationElement]$Root,[string]$Name){
    $All=$Root.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition)
    foreach($Item in $All){try{if((Normalize-UiName $Item.Current.Name) -eq (Normalize-UiName $Name) -and -not $Item.Current.IsOffscreen){return $Item}}catch{}}
    return $null
}
function Invoke-UiElement([System.Windows.Automation.AutomationElement]$Element){
    $Pattern=$null
    if($Element.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern,[ref]$Pattern)){$Pattern.Invoke();return}
    if($Element.TryGetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern,[ref]$Pattern)){$Pattern.Expand();return}
    if($Element.TryGetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern,[ref]$Pattern)){$Pattern.Select();return}
    if($Element.TryGetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern,[ref]$Pattern)){
        if($Pattern.Current.ToggleState -eq [System.Windows.Automation.ToggleState]::Off){$Pattern.Toggle()};return
    }
    # Managed .NET UIAutomation does not expose LegacyIAccessiblePattern.
    # For a named UIA element backed by a standard Win32 Button only, use its
    # documented BM_CLICK action, never coordinates or a guessed handle.
    if($Element.Current.ClassName -eq 'Button' -and $Element.Current.NativeWindowHandle -ne 0){
        if(-not [PS35.Native]::PostMessage([IntPtr]$Element.Current.NativeWindowHandle,0xF5,[IntPtr]::Zero,[IntPtr]::Zero)){throw 'BM_CLICK post failed'}
        return
    }
    throw "No public UIA action pattern: $($Element.Current.Name)"
}
function Invoke-NamedTwice([System.Windows.Automation.AutomationElement]$Root,[string]$Name,[string]$Tag){
    for($Attempt=1;$Attempt -le 2;$Attempt++){
        $Element=Find-Named $Root $Name
        if($null -ne $Element -and $Element.Current.IsEnabled){Invoke-UiElement $Element;return}
        Save-UiTree $Root "$Tag-attempt$Attempt";Save-Desktop "$Tag-attempt$Attempt";Start-Sleep -Seconds 3
    }
    throw "STOP_UIA_BUTTONS: '$Name' unavailable after two attempts; inspect saved UIA trees, do not invent coordinates"
}
function Wait-Open([uint32]$ProcessId){
    $End=[DateTime]::UtcNow.AddSeconds(60)
    do{$OpenWindows=@([PS35.Native]::Windows() | Where-Object {$_.ProcessId -eq $ProcessId -and $_.Text -eq 'Open'});if($OpenWindows.Count -gt 0){return $OpenWindows[0]};Start-Sleep -Milliseconds 500}while([DateTime]::UtcNow -lt $End)
    Save-Desktop 'open-timeout';throw 'Open dialog did not become visible'
}
function Save-OpenState([string]$Name,[uint32]$ProcessId){
    $Window=Wait-Open $ProcessId
    # Wait for the rect to settle rather than assuming the initial frame is final.
    for($i=0;$i -lt 20;$i++){
        Start-Sleep -Milliseconds 500;$Next=Wait-Open $ProcessId
        if($Next.Width -eq $Window.Width -and $Next.Height -eq $Window.Height -and $Next.Handle -eq $Window.Handle){$Window=$Next;break};$Window=$Next
    }
    Save-Desktop $Name
    $Window | Add-Member -NotePropertyName utc -NotePropertyValue ([DateTime]::UtcNow.ToString('o'))
    $Window | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $Out "$Name-rect.json")
    Write-Host "$Name hwnd=$($Window.Handle) outer=$($Window.Width)x$($Window.Height) client=$($Window.ClientWidth)x$($Window.ClientHeight) dpi=$($Window.Dpi)"
    return $Window
}
