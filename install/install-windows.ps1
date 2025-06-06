param(
  [switch]$Prerelease
)

$repoOwner = "frinshhd"
$repoName = "sumsnap"

if ($Prerelease) {
  Write-Host "Downloading latest *pre-release* sumsnap for Windows..."
  $releases = Invoke-RestMethod "https://api.github.com/repos/$repoOwner/$repoName/releases"
  $pre = $releases | Where-Object { $_.prerelease } | Select-Object -First 1
  $asset = $pre.assets | Where-Object { $_.name -like "sumsnap-windows*" } | Select-Object -First 1
  $url = $asset.browser_download_url
} else {
  Write-Host "Downloading latest sumsnap for Windows..."
  $release = Invoke-RestMethod "https://api.github.com/repos/$repoOwner/$repoName/releases/latest"
  $asset = $release.assets | Where-Object { $_.name -like "sumsnap-windows*" } | Select-Object -First 1
  $url = $asset.browser_download_url
}

if (-not $url) {
  Write-Host "No suitable binary found!"
  exit 1
}

Invoke-WebRequest -Uri $url -OutFile "sumsnap.exe"
Write-Host "Moving sumsnap.exe to C:\Windows\System32 (requires admin)..."
Move-Item -Path "sumsnap.exe" -Destination "C:\Windows\System32\sumsnap.exe" -Force
Write-Host "Installed! Run 'sumsnap' from anywhere."