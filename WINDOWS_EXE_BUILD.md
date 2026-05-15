# Build SPXBot.exe

## Option A: Build on the Windows laptop

1. Copy the project folder to Windows.
2. Double-click `setup_windows.bat`.
3. Double-click `build_windows_exe.bat`.

The finished files will be here:

```text
dist\SPXBot.exe
dist\.env
```

Run:

```text
dist\SPXBot.exe
```

## Option B: Build with GitHub Actions

1. Push this project to GitHub.
2. Open the repository on GitHub.
3. Go to `Actions`.
4. Select `Build Windows EXE`.
5. Click `Run workflow`.
6. Download the artifact named `SPXBot-Windows`.

The artifact contains:

```text
SPXBot.exe
.env
README.md
```

The user does not need Python to run `SPXBot.exe`.

If `SPXBot.exe` does not start, it writes a full traceback next to the executable:

```text
SPXBot_error.log
```

Send that file for debugging.

## Important

Windows `.exe` files must be built on Windows. Building on macOS creates a macOS app, not a Windows executable.
