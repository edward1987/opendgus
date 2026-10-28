<#
.SYNOPSIS
  Build an OpenDGUS release for Windows (installer + portable exe) and optionally publish it on GitHub.

.DESCRIPTION
  1. checks the tools and the git tree
  2. sets the version everywhere (app/package.json, pyproject.toml, src/opendgus/__init__.py) when -Version is given
  3. runs the tests (pytest, typecheck, vitest) unless -SkipTests
  4. builds the Python sidecar with PyInstaller and smoke-tests it
  5. builds the Electron installers with electron-builder
  6. copies the files to release\v<version>\ with SHA256SUMS.txt and RELEASE_NOTES.md
  7. with -Publish: tags v<version>, pushes the tag and creates a DRAFT GitHub release with the files (gh CLI)

  Pushing the tag also starts .github/workflows/release.yml, which adds the macOS and Linux builds to the
  same release. Review the draft on GitHub, then press "Publish release".

.EXAMPLE
  .\build-release.ps1                      # build the version in app/package.json
  .\build-release.ps1 -Version 0.7.0       # bump to 0.7.0 and build
  .\build-release.ps1 -Version 0.7.0 -Publish
#>
[CmdletBinding()]
param(
  [string]$Version,         # e.g. 0.7.0; default = current app/package.json version
  [switch]$SkipTests,
  [switch]$CleanInstall,    # npm ci even when node_modules exists
  [switch]$Publish,         # tag + push + draft GitHub release
  [switch]$AllowDirty       # build even with uncommitted changes
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$App = Join-Path $Root "app"
$Utf8 = New-Object System.Text.UTF8Encoding($false)

function Step($msg) { Write-Host ""; Write-Host "==> $msg" -ForegroundColor Cyan }
function Fail($msg) { Write-Host "ERROR: $msg" -ForegroundColor Red; exit 1 }

# Run a native command and stop on a non-zero exit code.
function Run {
  param([string]$Exe, [string[]]$ArgList, [string]$Dir = $Root)
  Write-Host "> $Exe $($ArgList -join ' ')" -ForegroundColor DarkGray
  Push-Location $Dir
  try { & $Exe @ArgList } finally { Pop-Location }
  if ($LASTEXITCODE -ne 0) { Fail "$Exe exited with code $LASTEXITCODE" }
}

# Run a native command whose failure is expected/handled (PS 5.1 turns redirected stderr into errors under Stop).
function Try-Native([scriptblock]$Block) {
  $old = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try { $out = & $Block 2>$null; return @{ Ok = ($LASTEXITCODE -eq 0); Out = $out } } finally { $ErrorActionPreference = $old }
}

function Replace-InFile($path, $pattern, $replacement) {
  $text = [IO.File]::ReadAllText($path)
  $re = New-Object System.Text.RegularExpressions.Regex($pattern, "Multiline")
  if (-not $re.IsMatch($text)) { Fail "no version found in $path" }
  [IO.File]::WriteAllText($path, $re.Replace($text, $replacement, 1), $Utf8)
}

# ------------------------------------------------------------------ 1. tools and tree
Step "Checking tools"
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { Fail ".venv not found. Create it: python -m venv .venv; .venv\Scripts\pip install -e "".[dev,build]""" }
foreach ($t in @("node", "npm", "git")) {
  if (-not (Get-Command $t -ErrorAction SilentlyContinue)) { Fail "$t is not on PATH" }
}
if (-not (Try-Native { & $Python -c "import PyInstaller" }).Ok) { Fail "PyInstaller missing: .venv\Scripts\pip install -e "".[build]""" }
if ($Publish -and -not (Get-Command gh -ErrorAction SilentlyContinue)) { Fail "-Publish needs the GitHub CLI (gh)" }
Write-Host "node $(node --version), $(& $Python --version)"

Push-Location $Root
$dirty = git status --porcelain
$branch = git rev-parse --abbrev-ref HEAD
Pop-Location
if ($dirty -and -not $AllowDirty) { Fail "uncommitted changes (commit them, or use -AllowDirty for a test build)" }

# ------------------------------------------------------------------ 2. version
$pkgPath = Join-Path $App "package.json"
$current = (Get-Content $pkgPath -Raw | ConvertFrom-Json).version
if (-not $Version) { $Version = $current }
$Version = $Version.TrimStart("v")
if ($Version -notmatch '^\d+\.\d+\.\d+([-.][0-9A-Za-z.]+)?$') { Fail "version '$Version' is not like 1.2.3" }
$Tag = "v$Version"

Step "Version $Version"
Replace-InFile $pkgPath '^(  "version":\s*")[^"]+(")' "`${1}$Version`${2}"
Replace-InFile (Join-Path $Root "pyproject.toml") '^(version\s*=\s*")[^"]+(")' "`${1}$Version`${2}"
Replace-InFile (Join-Path $Root "src\opendgus\__init__.py") '^(__version__\s*=\s*")[^"]+(")' "`${1}$Version`${2}"
# the lock file carries the version twice (root + packages[""])
$lockPath = Join-Path $App "package-lock.json"
$lock = [IO.File]::ReadAllText($lockPath)
$lock = ([regex]'(?m)^(  "version":\s*")[^"]+(")').Replace($lock, "`${1}$Version`${2}", 1)
$lock = ([regex]'(?m)^(      "version":\s*")[^"]+(")').Replace($lock, "`${1}$Version`${2}", 1)
[IO.File]::WriteAllText($lockPath, $lock, $Utf8)

if ($Publish) {
  Push-Location $Root
  $tagExists = git tag --list $Tag
  Pop-Location
  if ($tagExists) { Fail "tag $Tag already exists; pick a new -Version" }
}

# ------------------------------------------------------------------ 3. dependencies and tests
if ($CleanInstall -or -not (Test-Path (Join-Path $App "node_modules"))) {
  Step "Installing app dependencies"
  Run "npm" @("ci") $App
}

if (-not $SkipTests) {
  Step "Python tests"
  Run $Python @("-m", "pytest", "-q") $Root
  Step "Typecheck + frontend tests"
  Run "npm" @("run", "typecheck") $App
  Run "npm" @("test") $App
}

# ------------------------------------------------------------------ 4. Python sidecar
Step "Cleaning old build output"
foreach ($d in @("packaging\dist", "packaging\build", "app\release")) {
  $p = Join-Path $Root $d
  if (Test-Path $p) { Remove-Item $p -Recurse -Force }
}

Step "Building the Python sidecar (PyInstaller)"
$env:OPENDGUS_PYTHON = $Python
Run "node" @("scripts/dist-backend.mjs") $App

Step "Smoke-testing the sidecar"
$server = Join-Path $Root "packaging\dist\opendgus-backend\opendgus-server.exe"
$readyFile = Join-Path $env:TEMP "opendgus-ready-$PID.txt"
$proc = Start-Process -FilePath $server -ArgumentList "--port", "0" -RedirectStandardOutput $readyFile -PassThru -WindowStyle Hidden
try {
  $ready = $null
  for ($i = 0; $i -lt 60 -and -not $ready; $i++) {
    Start-Sleep -Seconds 1
    if ($proc.HasExited) { Fail "sidecar exited with code $($proc.ExitCode)" }
    $line = Get-Content $readyFile -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($line -match '"ready"') { $ready = $line | ConvertFrom-Json }
  }
  if (-not $ready) { Fail "sidecar did not report ready within 60 s" }
  $health = Invoke-RestMethod "http://127.0.0.1:$($ready.port)/api/health" -Headers @{ "X-OpenDGUS-Token" = $ready.token }
  if (-not $health.ok) { Fail "health check failed" }
  Write-Host "sidecar OK, version $($health.version)" -ForegroundColor Green
  if ($health.version -ne $Version) { Fail "sidecar reports version $($health.version), expected $Version" }
} finally {
  if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
  Remove-Item $readyFile -ErrorAction SilentlyContinue
}

# ------------------------------------------------------------------ 5. Electron installers
Step "Building the installers (electron-builder)"
$env:CSC_IDENTITY_AUTO_DISCOVERY = "false"   # unsigned
Run "npm" @("run", "dist:app") $App

# ------------------------------------------------------------------ 6. collect
Step "Collecting files"
$out = Join-Path $Root "release\$Tag"
if (Test-Path $out) { Remove-Item $out -Recurse -Force }
New-Item -ItemType Directory -Force $out | Out-Null
$files = Get-ChildItem (Join-Path $App "release") -File | Where-Object { $_.Extension -in ".exe", ".blockmap" -or $_.Name -eq "latest.yml" }
if (-not ($files | Where-Object { $_.Name -like "*Setup*.exe" })) { Fail "no installer found in app\release" }
$files | Copy-Item -Destination $out

$sums = Get-ChildItem $out -File -Filter *.exe | ForEach-Object {
  "$((Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower())  $($_.Name)"
}
[IO.File]::WriteAllText((Join-Path $out "SHA256SUMS.txt"), (($sums -join "`n") + "`n"), $Utf8)

# notes: commits since the previous tag (or all of them for the first release)
Push-Location $Root
$d = Try-Native { git describe --tags --abbrev=0 }
$prev = if ($d.Ok) { "$($d.Out)".Trim() } else { $null }
$range = if ($prev) { "$prev..HEAD" } else { "HEAD" }
$log = @(git log $range --no-merges --pretty=format:"- %s")
Pop-Location
$changes = if ($prev) { "### Changes since $prev" } else { "### Changes" }
$lines = @(
  "## OpenDGUS $Version", "",
  "### Downloads",
  "- **OpenDGUS-Setup-$Version-x64.exe**: Windows installer",
  "- **OpenDGUS-$Version-portable-x64.exe**: Windows portable, no install needed",
  "- macOS (.dmg) and Linux (.AppImage) are added by the release workflow", "",
  "The builds are not code-signed: Windows SmartScreen may ask you to confirm (More info > Run anyway).", "",
  $changes)
$lines += $log
$lines += @("", "SHA-256 checksums are in SHA256SUMS.txt.")
$notes = $lines -join "`n"
[IO.File]::WriteAllText((Join-Path $out "RELEASE_NOTES.md"), $notes, $Utf8)

Get-ChildItem $out | ForEach-Object { Write-Host ("  {0,-45} {1,8:N1} MB" -f $_.Name, ($_.Length / 1MB)) }

# ------------------------------------------------------------------ 7. publish
if ($Publish) {
  Step "Publishing $Tag on GitHub (draft)"
  if ($Version -ne $current) {
    Run "git" @("add", "app/package.json", "app/package-lock.json", "pyproject.toml", "src/opendgus/__init__.py")
    Run "git" @("commit", "-m", "Release $Version")
    Run "git" @("push", "origin", $branch)
  }
  Run "git" @("tag", "-a", $Tag, "-m", "OpenDGUS $Version")
  Run "git" @("push", "origin", $Tag)
  $assets = Get-ChildItem $out -File | Where-Object { $_.Name -ne "RELEASE_NOTES.md" } | ForEach-Object { $_.FullName }
  Run "gh" (@("release", "create", $Tag, "--draft", "--title", "OpenDGUS $Version", "--notes-file", (Join-Path $out "RELEASE_NOTES.md")) + $assets)
  Write-Host ""
  Write-Host "Draft release created. Review it, then press 'Publish release':" -ForegroundColor Green
  Run "gh" @("release", "view", $Tag, "--web")
} else {
  Write-Host ""
  Write-Host "Done: $out" -ForegroundColor Green
  if ($Version -ne $current) { Write-Host "Version changed $current -> ${Version}: commit the version files before publishing." -ForegroundColor Yellow }
  Write-Host "To publish: .\build-release.ps1 -Version $Version -Publish   (or upload the files in a new GitHub release)"
}
