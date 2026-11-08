# Task35 only: normal CS2 trial installation, then public UIA/Win32 observations.
. (Join-Path $PSScriptRoot 'ps35-uia.ps1')
$RawInstallLog=Join-Path $env:RUNNER_TEMP 'ps35-install-raw.log'
$Application=$null
function Export-InstallLog {
    if(Test-Path $RawInstallLog){
        Get-Content $RawInstallLog | ForEach-Object {
            if($_ -match '(?i)serial|product.?key|cdkey|regcode|pidkey'){'<license-related MSI log line redacted>'}
            else{$_ -replace '\b\d{4}(?:-\d{4}){5}\b','<redacted>'}
        } | Set-Content (Join-Path $Out 'msi-install-redacted.log')
    }
}
function Install-WithWizard {
    $SetupRoot=Join-Path $Source 'Photoshop CS2'
    $Args='/i "{0}" /norestart UNITYSELECTION=TRYOUT ACCEPTEDEULA=1 SETUPEXEDIR="{1}" /l*v "{2}"' -f $Msi.FullName,$SetupRoot,$RawInstallLog
    $Client=Start-Process msiexec.exe -ArgumentList $Args -PassThru
    $Deadline=[DateTime]::UtcNow.AddMinutes(12);$Step=0
    while([DateTime]::UtcNow -lt $Deadline){
        if([PS35.Native]::MsiQueryProductState('{236BB7C4-4419-42FD-0409-1E257A25E34D}') -eq 5 -and $Client.HasExited){return}
        $Windows=@([PS35.Native]::Windows() | Where-Object {$_.Text -match 'Photoshop CS2|License Agreement'})
        if($Windows.Count -eq 0){if($Client.HasExited){throw "MSI GUI client exited $($Client.ExitCode) without installed state"};Start-Sleep -Seconds 1;continue}
        $Window=$Windows[0];$Root=[System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]$Window.Handle)
        if($Window.Text -match '(?i)invalid serial|activation|expired'){Save-UiTree $Root 'install-blocked';Save-Desktop 'install-blocked';throw 'STOP_LICENSE: installer requests serial/activation or reports expiry'}
        $Trial=Find-Named $Root 'Install 30-day trial version'
        if($null -ne $Trial){
            $Pattern=$null
            if($Trial.TryGetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern,[ref]$Pattern)){$Pattern.Select()}else{Invoke-UiElement $Trial}
            Start-Sleep -Milliseconds 500
            $Edits=$Root.FindAll([System.Windows.Automation.TreeScope]::Descendants,(New-Object System.Windows.Automation.PropertyCondition ([System.Windows.Automation.AutomationElement]::ControlTypeProperty),([System.Windows.Automation.ControlType]::Edit)))
            $Fields=@($Edits | Where-Object {$_.Current.IsEnabled -and -not $_.Current.IsOffscreen -and $_.Current.Name -notmatch '(?i)serial'} | Sort-Object {$_.Current.BoundingRectangle.Y})
            if($Fields.Count -ne 2){Save-UiTree $Root 'trial-fields';Save-Desktop 'trial-fields';throw 'Trial UI does not expose exactly two enabled non-serial identity fields'}
            for($i=0;$i -lt 2;$i++){$P=$Fields[$i].GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern);$P.SetValue(@('Compatibility Test','CI task35')[$i])}
            Save-Desktop 'trial-selected'
        }
        $Advanced=$false
        foreach($Name in @('Accept','I accept the terms in the license agreement','Next','Install','Finish')){
            $Element=Find-Named $Root $Name
            if($null -ne $Element -and $Element.Current.IsEnabled){Invoke-UiElement $Element;$Advanced=$true;break}
        }
        if(-not $Advanced){$Step++;if($Step -le 2){Save-UiTree $Root "install-wait$Step";Save-Desktop "install-wait$Step"}}
        Start-Sleep -Seconds 1
    }
    Save-Desktop 'install-timeout';throw 'MSI GUI did not finish within12minutes'
}
try {
    $SetupRoot=Join-Path $Source 'Photoshop CS2'
    # Public MSI metadata shows UNITYSELECTION=TRYOUT is the vendor trial path.
    # Never read/pass SERIALNUMBERTRYOUT or a serial. If /qn needs UI events,
    # fall back to the unmodified wizard's normal trial radio selection.
    $Args='/i "{0}" /qn /norestart UNITYSELECTION=TRYOUT USERNAME="Compatibility Test" COMPANYNAME="CI task35" ACCEPTEDEULA=1 AgreeToLicense=Yes SETUPEXEDIR="{1}" /l*v "{2}"' -f $Msi.FullName,$SetupRoot,$RawInstallLog
    $Install=Start-Process msiexec.exe -ArgumentList $Args -PassThru
    if(-not $Install.WaitForExit(600000)){Stop-Process -Id $Install.Id -ErrorAction SilentlyContinue;throw 'Silent MSI timed out; no concurrent GUI retry'}
    @{mode='normal vendor trial flag; no serial';silent_exit=$Install.ExitCode;utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content (Join-Path $Out 'installation.json')
    if($Install.ExitCode -notin @(0,3010)){
        Export-InstallLog
        Copy-Item (Join-Path $Out 'msi-install-redacted.log') (Join-Path $Out 'msi-silent-redacted.log')
        Install-WithWizard
    }
    Export-InstallLog
    $State=[PS35.Native]::MsiQueryProductState('{236BB7C4-4419-42FD-0409-1E257A25E34D}')
    $Exe=Join-Path ${env:ProgramFiles(x86)} 'Adobe/Adobe Photoshop CS2/Photoshop.exe'
    if($State -ne 5 -or -not(Test-Path $Exe)){throw "Installation not verified: state=$State expected EXE=$Exe"}
    $Hash=(Get-FileHash $Exe -Algorithm SHA256).Hash.ToLower()
    if($Hash -ne '98c746a4707a875f8077d79550f7129b459ae784de05b05f349f89ddecf56d30'){throw 'Installed Photoshop.exe hash mismatch'}
    @{state=$State;exe_sha256=$Hash;dpi=[PS35.Native]::GetDpiForSystem()} | ConvertTo-Json | Set-Content (Join-Path $Out 'installed.json')
    $Application=Start-Process $Exe -WorkingDirectory (Split-Path $Exe) -PassThru
    $Main=$null;$Deadline=[DateTime]::UtcNow.AddMinutes(8)
    do {
        $Candidates=@([PS35.Native]::Windows() | Where-Object {$_.ClassName -eq 'Photoshop'})
        if($Candidates.Count -gt 0){
            $Main=$Candidates[0];$Root=[System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]$Main.Handle)
            $File=Find-Named $Root 'File'
            if($null -ne $File -and $File.Current.IsEnabled){break}
        }
        foreach($Window in @([PS35.Native]::Windows() | Where-Object {$_.ProcessId -eq $Application.Id})){
            $Dialog=[System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]$Window.Handle)
            $Continue=Find-Named $Dialog 'Continue Trial'
            if($null -ne $Continue){Invoke-UiElement $Continue}
            if($Window.Text -match '(?i)expired|activation|serial'){Save-UiTree $Dialog 'startup-blocked';Save-Desktop 'startup-blocked';throw 'STOP_LICENSE: normal trial startup blocked'}
        }
        Start-Sleep -Seconds 1
    }while([DateTime]::UtcNow -lt $Deadline)
    if($null -eq $Main -or $null -eq $File){Save-Desktop 'startup-timeout';throw 'Full main menu not ready; inspect startup artifact'}
    $WindowPattern=$null
    if($Root.TryGetCurrentPattern([System.Windows.Automation.WindowPattern]::Pattern,[ref]$WindowPattern)){$WindowPattern.SetWindowVisualState([System.Windows.Automation.WindowVisualState]::Maximized)}
    Save-Desktop 'workspace'
    Invoke-NamedTwice $Root 'File' 'file-menu'
    Start-Sleep -Milliseconds 500
    Invoke-NamedTwice ([System.Windows.Automation.AutomationElement]::RootElement) 'Open' 'file-open'
    $Before=Save-OpenState 'os-before' $Main.ProcessId
    $OpenRoot=[System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]$Before.Handle)
    Save-UiTree $OpenRoot 'os-before'
    Invoke-NamedTwice $OpenRoot 'Use Adobe Dialog' 'use-adobe'
    $Adobe=Save-OpenState 'adobe' $Main.ProcessId
    $OpenRoot=[System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]$Adobe.Handle)
    Save-UiTree $OpenRoot 'adobe'
    Invoke-NamedTwice $OpenRoot 'Use OS Dialog' 'use-os'
    $After=Save-OpenState 'os-after' $Main.ProcessId
    $Result=@{os_before=$Before;adobe=$Adobe;os_after=$After;original_os_hwnd_preserved=($Before.Handle -eq $After.Handle);width_growth=($After.Width-$Before.Width);utc=[DateTime]::UtcNow.ToString('o')}
    $Result | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $Out 'comparison.json')
    Write-Host ($Result | ConvertTo-Json -Depth 6 -Compress)
}finally{
    Export-InstallLog
    if($null -ne $Application){
        foreach($Window in @([PS35.Native]::Windows() | Where-Object {$_.ProcessId -eq $Application.Id -and $_.Text -eq 'Open'})){[PS35.Native]::PostMessage([IntPtr]$Window.Handle,0x10,[IntPtr]::Zero,[IntPtr]::Zero) | Out-Null}
        Start-Sleep -Seconds 1
        foreach($Window in @([PS35.Native]::Windows() | Where-Object {$_.ProcessId -eq $Application.Id -and $_.ClassName -eq 'Photoshop'})){[PS35.Native]::PostMessage([IntPtr]$Window.Handle,0x10,[IntPtr]::Zero,[IntPtr]::Zero) | Out-Null}
    }
}
