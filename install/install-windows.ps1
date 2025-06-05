$REPO_OWNER = "frinshhd"
$REPO_NAME = "sumsnap"
$exe = "sumsnap-windows.exe"
$finalExe = "sumsnap.exe"
Write-Host "Downloading latest sumsnap for Windows..."
$api = "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/releases/latest"
$url = (Invoke-RestMethod $api).assets | Where-Object { $_.name -eq $exe } | Select-Object -ExpandProperty browser_download_url
Invoke-WebRequest -Uri $url -OutFile $finalExe
Write-Host "Downloaded $finalExe to current directory."
$destDir = "$env:USERPROFILE\AppData\Local\Programs\sumsnap"
$dest = "$destDir\sumsnap.exe"
$move = Read-Host "Move to $dest for global use (and add to PATH if needed)? (y/N)"
if ($move -eq "y") {
    if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir | Out-Null }
    Move-Item $finalExe $dest -Force
    Write-Host "Moved to $dest."
    $userPath = [System.Environment]::GetEnvironmentVariable("PATH", "User")
    if ($userPath -notlike "*$destDir*") {
        [System.Environment]::SetEnvironmentVariable("PATH", "$userPath;$destDir", "User")
        Write-Host "Added $destDir to your PATH. You may need to restart your terminal."
    }
    Write-Host "You can now run 'sumsnap' from anywhere."
} else {
    Write-Host "You can run it from the current directory: $PWD\$finalExe"
}