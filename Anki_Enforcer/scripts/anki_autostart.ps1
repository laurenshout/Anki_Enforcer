param(
    [ValidateSet("status", "enable", "disable")]
    [string]$Action = "status",
    [string]$AnkiPath = "",
    [string]$ShortcutName = "Anki.lnk",
    [string]$LauncherName = "AnkiHiddenLauncher.vbs"
)

$ErrorActionPreference = "Stop"

function Get-DefaultAnkiPath {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Anki\anki.exe"),
        "C:\Program Files\Anki\anki.exe",
        "C:\Program Files (x86)\Anki\anki.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }
    return ""
}

function Resolve-AnkiExecutable([string]$CandidatePath) {
    if ([string]::IsNullOrWhiteSpace($CandidatePath)) {
        return ""
    }
    if (-not (Test-Path $CandidatePath)) {
        return ""
    }

    $resolved = [System.IO.Path]::GetFullPath($CandidatePath)
    $leaf = [System.IO.Path]::GetFileName($resolved)
    if ($leaf -ieq "anki.exe") {
        return $resolved
    }

    if ($leaf -ieq "pythonw.exe" -or $leaf -ieq "python.exe") {
        $searchDir = Split-Path -Parent $resolved
        for ($i = 0; $i -lt 5 -and $searchDir; $i++) {
            $candidates = @(
                (Join-Path $searchDir "anki.exe"),
                (Join-Path $searchDir "Scripts\anki.exe"),
                (Join-Path $searchDir ".venv\Scripts\anki.exe")
            )
            foreach ($ankiCandidate in $candidates) {
                if (Test-Path $ankiCandidate) {
                    return $ankiCandidate
                }
            }
            $parent = Split-Path -Parent $searchDir
            if ($parent -eq $searchDir) {
                break
            }
            $searchDir = $parent
        }
    }

    return $resolved
}

function Get-StartupShortcutPath([string]$Name) {
    $startupDir = [Environment]::GetFolderPath("Startup")
    return (Join-Path $startupDir $Name)
}

function Get-StartupLauncherPath([string]$Name) {
    $startupDir = [Environment]::GetFolderPath("Startup")
    return (Join-Path $startupDir $Name)
}

function Read-ShortcutTarget([string]$ShortcutPath) {
    if (-not (Test-Path $ShortcutPath)) {
        return ""
    }
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($ShortcutPath)
    return [string]$shortcut.TargetPath
}

function Read-ShortcutArguments([string]$ShortcutPath) {
    if (-not (Test-Path $ShortcutPath)) {
        return ""
    }
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($ShortcutPath)
    return [string]$shortcut.Arguments
}

function Write-Shortcut([string]$ShortcutPath, [string]$TargetPath, [string]$Arguments, [string]$WorkingDirectory) {
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($ShortcutPath)
    $shortcut.TargetPath = $TargetPath
    $shortcut.Arguments = $Arguments
    $shortcut.WorkingDirectory = $WorkingDirectory
    $shortcut.WindowStyle = 7
    $shortcut.Description = "Launch Anki at Windows login"
    $shortcut.Save()
}

function Write-LauncherScript([string]$LauncherPath, [string]$TargetPath) {
    $escapedTarget = $TargetPath.Replace("""", """""")
    $launcherBody = @(
        'Set shell = CreateObject("WScript.Shell")',
        'shell.Run """" & "' + $escapedTarget + '" & """", 0, False'
    )
    Set-Content -Path $LauncherPath -Value $launcherBody -Encoding ASCII
}

$resolvedAnkiPath = if ([string]::IsNullOrWhiteSpace($AnkiPath)) {
    Resolve-AnkiExecutable (Get-DefaultAnkiPath)
} else {
    Resolve-AnkiExecutable $AnkiPath
}

$shortcutPath = Get-StartupShortcutPath $ShortcutName
$launcherPath = Get-StartupLauncherPath $LauncherName

switch ($Action) {
    "status" {
        $exists = Test-Path $shortcutPath
        $target = Read-ShortcutTarget $shortcutPath
        $arguments = Read-ShortcutArguments $shortcutPath
        Write-Output ("Autostart enabled: " + ($exists -and $target))
        Write-Output ("Shortcut path: " + $shortcutPath)
        Write-Output ("Shortcut target: " + $target)
        Write-Output ("Shortcut arguments: " + $arguments)
        Write-Output ("Launcher path: " + $launcherPath)
        if (-not $resolvedAnkiPath) {
            Write-Output "Detected Anki path: <not found>"
        } else {
            Write-Output ("Detected Anki path: " + $resolvedAnkiPath)
        }
    }
    "enable" {
        if ([string]::IsNullOrWhiteSpace($resolvedAnkiPath)) {
            throw "Could not detect Anki path automatically. Pass -AnkiPath explicitly."
        }
        if (-not (Test-Path $resolvedAnkiPath)) {
            throw "Anki path does not exist: $resolvedAnkiPath"
        }
        Write-LauncherScript -LauncherPath $launcherPath -TargetPath $resolvedAnkiPath
        Write-Shortcut `
            -ShortcutPath $shortcutPath `
            -TargetPath "$env:SystemRoot\System32\wscript.exe" `
            -Arguments ('"' + $launcherPath + '"') `
            -WorkingDirectory (Split-Path -Parent $resolvedAnkiPath)
        Write-Output ("Enabled Anki autostart using shortcut: " + $shortcutPath)
    }
    "disable" {
        if (Test-Path $shortcutPath) {
            Remove-Item -Path $shortcutPath -Force
            Write-Output ("Disabled Anki autostart (removed): " + $shortcutPath)
        } else {
            Write-Output "Autostart shortcut not found; nothing to disable."
        }
        if (Test-Path $launcherPath) {
            Remove-Item -Path $launcherPath -Force
            Write-Output ("Removed autostart launcher: " + $launcherPath)
        }
    }
}
