# #78/#82 on Windows (public APIs only): after a click into a floating
# palette, which window is foreground/active/focused, and what does Alt+F4
# close? Dot-sourced by ps35-measure.ps1 when PS35_ONLY=palette, with $Main
# (Photoshop main window) and $Out set; writes palette.json + screenshots.
function Get-PsWindows {
    @([PS35.Native]::Windows() | Where-Object {$_.ProcessId -eq $Main.ProcessId} | ForEach-Object {
        $H=[IntPtr]$_.Handle
        [ordered]@{handle=$_.Handle;class=$_.ClassName;text=$_.Text;x=$_.X;y=$_.Y;w=$_.Width;h=$_.Height
            style=('{0:X8}' -f [PS35.Native]::GetWindowLong($H,-16));exstyle=('{0:X8}' -f [PS35.Native]::GetWindowLong($H,-20))
            owner=[PS35.Native]::GetWindow($H,4).ToInt64()}
    })
}
function Get-Focus([string]$Tag){
    $T=[PS35.Native]::ThreadState([IntPtr]$Main.Handle)
    [ordered]@{tag=$Tag;foreground=[PS35.Native]::GetForegroundWindow().ToInt64();active=$T[0];focus=$T[1];flags=$T[2]
        main_exists=[bool](@([PS35.Native]::Windows() | Where-Object {$_.Handle -eq $Main.Handle}).Count)}
}
$Result=[ordered]@{main=$Main.Handle}
[void][PS35.Native]::SetForegroundWindow([IntPtr]$Main.Handle);Start-Sleep -Seconds 1
$Result.windows=Get-PsWindows
$Result.before=Get-Focus 'before'
# The History palette: an owned, visible window of the process whose text or
# UIA name says History; fallback: any owned popup that is not a dialog.
$Palette=@($Result.windows | Where-Object {$_.owner -eq $Main.Handle -and $_.text -match 'History'})
if($Palette.Count -eq 0){
    foreach($W in @($Result.windows | Where-Object {$_.owner -eq $Main.Handle})){
        $Name=([System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]$W.handle)).Current.Name
        if($Name -match 'History'){$Palette=@($W);break}
    }
}
if($Palette.Count -eq 0){$Palette=@($Result.windows | Where-Object {$_.owner -eq $Main.Handle -and $_.w -gt 100 -and $_.h -gt 100} | Sort-Object {$_.x} -Descending)}
Save-Desktop 'palette-before'
if($Palette.Count -gt 0){
    $P=$Palette[0];$Result.palette=$P
    # Lower half of the palette: list rows, away from the tab strip
    [PS35.Native]::Click([int]($P.x+$P.w/2),[int]($P.y+$P.h*2/3));Start-Sleep -Seconds 2
    $Result.after_click=Get-Focus 'after-click'
    $Result.windows_after_click=Get-PsWindows
    Save-Desktop 'palette-after-click'
    # Alt+F4 with the palette clicked last
    [PS35.Native]::Key(0x12,$false);[PS35.Native]::Key(0x73,$false);[PS35.Native]::Key(0x73,$true);[PS35.Native]::Key(0x12,$true)
    Start-Sleep -Seconds 3
    $Result.after_altf4=Get-Focus 'after-alt-f4'
    $Result.windows_after_altf4=Get-PsWindows
    Save-Desktop 'palette-after-altf4'
}else{$Result.error='no palette found'}
$Result | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $Out 'palette.json')
Write-Host ($Result | ConvertTo-Json -Depth 6 -Compress)
