# Windows Smart App Control

Windows Smart App Control can block self-built unsigned `.exe` files. This is common for PyInstaller apps.

## Recommended Fix

Sign `SPXBot.exe` with a code-signing certificate.

The GitHub Actions workflow supports signing if these repository secrets exist:

```text
WINDOWS_CERTIFICATE_BASE64
WINDOWS_CERTIFICATE_PASSWORD
```

`WINDOWS_CERTIFICATE_BASE64` must be a base64-encoded `.pfx` code-signing certificate.

PowerShell command to create the base64 value:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\path\to\certificate.pfx")) | Set-Clipboard
```

Add the copied value in GitHub:

```text
Repository > Settings > Secrets and variables > Actions > New repository secret
```

Then run the `Build Windows EXE` workflow again.

## Temporary Workaround

For private testing only, the user can turn off Smart App Control:

```text
Windows Security > App & browser control > Smart App Control settings
```

This is not recommended for general distribution. On many Windows installations, once Smart App Control is turned off, it cannot simply be turned back on without resetting Windows.

## Why This Happens

The app is locally built and has no publisher reputation. Signing gives Windows a verified publisher identity and is the proper route for a normal installable app.
