$REPO_OWNER = "frinshhd"
$REPO_NAME = "sumsnap"
$exe = "sumsnap-windows.exe"
Write-Host "Downloading latest sumsnap for Windows..."
$api = "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/releases/latest"
$url = (Invoke-RestMethod $api).assets | Where-Object { $_.name -eq $exe } | Select-Object -ExpandProperty browser_download_url
Invoke-WebRequest -Uri $url -OutFile $exe
Write-Host "Downloaded $exe to current directory."
$dest = "$env:USERPROFILE\AppData\Local\Microsoft\WindowsApps\$exe"
$move = Read-Host "Move to $dest for global use? (y/N)"
if ($move -eq "y") {
    Move-Item $exe $dest -Force
    Write-Host "Moved to $dest. You can now run 'sumsnap-windows.exe' from anywhere."
} else {
    Write-Host "You can run it from the current directory: $PWD\$exe"
}