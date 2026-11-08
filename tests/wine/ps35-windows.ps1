param([ValidateSet('inspect','measure')][string]$Stage='inspect')
$ErrorActionPreference='Stop'
$Out=Join-Path $env:GITHUB_WORKSPACE 'ps35-evidence'
New-Item -ItemType Directory -Force $Out | Out-Null
Start-Transcript -Path (Join-Path $Out 'transcript.txt') | Out-Null
try {
    $Source=Join-Path $env:RUNNER_TEMP 'ps35-source'
    New-Item -ItemType Directory -Force $Source | Out-Null
    & 7z x (Join-Path $env:RUNNER_TEMP 'ps35-download/Photoshop_CS2.exe') "-o$Source" -y | Out-File (Join-Path $Out 'extraction.txt')
    if($LASTEXITCODE -ne 0){throw "7z failed: $LASTEXITCODE"}
    $Msi=Get-ChildItem $Source -Recurse -Filter 'Adobe Photoshop CS2.msi' | Select-Object -First 1
    if(-not $Msi){throw 'Verified archive contains no expected Photoshop MSI'}
    if(-not(Test-Path (Join-Path $Source 'Photoshop CS2/Setup.exe'))){throw 'Setup.exe missing'}
    $Installer=New-Object -ComObject WindowsInstaller.Installer
    $Db=$Installer.GetType().InvokeMember('OpenDatabase','InvokeMethod',$null,$Installer,@($Msi.FullName,0))
    function Read-MsiTable([string]$Name){
        $View=$Db.GetType().InvokeMember('OpenView','InvokeMethod',$null,$Db,@('SELECT * FROM `'+$Name+'`'))
        $View.GetType().InvokeMember('Execute','InvokeMethod',$null,$View,$null) | Out-Null
        $Rows=@()
        while($null -ne ($Record=$View.GetType().InvokeMember('Fetch','InvokeMethod',$null,$View,$null))){
            $Count=$Record.GetType().InvokeMember('FieldCount','GetProperty',$null,$Record,$null)
            $Cells=@();for($i=1;$i -le $Count;$i++){$Cells+= $Record.GetType().InvokeMember('StringData','GetProperty',$null,$Record,@($i))}
            # Property values that may contain serial/license data are never exported.
            if($Name -eq 'Property' -and $Cells[0] -match '(?i)serial|product.?key|cdkey|regcode|^PID'){$Cells[1]='<redacted>'}
            $Rows+=,@($Cells)
        }
        $View.GetType().InvokeMember('Close','InvokeMethod',$null,$View,$null) | Out-Null
        ConvertTo-Json -InputObject $Rows -Depth 8 | Set-Content (Join-Path $Out "msi-$Name.json")
    }
    foreach($Table in @('Property','Control','ControlEvent','InstallUISequence','LaunchCondition')){Read-MsiTable $Table}
    Add-Type -AssemblyName System.Windows.Forms,System.Drawing,UIAutomationClient,UIAutomationTypes
    $Screen=[System.Windows.Forms.SystemInformation]::VirtualScreen
    $Metadata=@{stage=$Stage;os=[System.Environment]::OSVersion.VersionString;interactive=[System.Environment]::UserInteractive;screen=@{x=$Screen.X;y=$Screen.Y;width=$Screen.Width;height=$Screen.Height};msi=$Msi.FullName;utc=[DateTime]::UtcNow.ToString('o')}
    $Metadata | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $Out 'environment.json')
    $Bitmap=New-Object System.Drawing.Bitmap $Screen.Width,$Screen.Height
    $Graphics=[System.Drawing.Graphics]::FromImage($Bitmap)
    try{$Graphics.CopyFromScreen($Screen.Location,[System.Drawing.Point]::Empty,$Screen.Size);$Bitmap.Save((Join-Path $Out 'desktop.png'))}finally{$Graphics.Dispose();$Bitmap.Dispose()}
    if($Stage -ne 'inspect'){throw 'Measurement stage will follow verified MSI trial property discovery; no guessed properties used'}
    Write-Host 'MSI public database and runner desktop inspection complete; no installation attempted.'
}finally{Stop-Transcript | Out-Null}
