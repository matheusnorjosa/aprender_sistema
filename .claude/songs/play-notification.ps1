Add-Type -AssemblyName presentationCore
$player = New-Object System.Windows.Media.MediaPlayer
$player.Open("$PSScriptRoot\duolingo-correct.mp3")
$player.Play()
Start-Sleep -Milliseconds 1500
