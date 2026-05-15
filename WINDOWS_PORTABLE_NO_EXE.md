# Portable Windows Version Without Custom EXE

Use this if Windows Smart App Control blocks the unsigned `SPXBot.exe`.

This method does **not** create a custom `.exe`. Instead, it bundles the official Python runtime from python.org and starts the app with a `.bat` file.

Why this helps:

- `python.exe` from python.org is signed by the Python Software Foundation.
- There is no unsigned custom `SPXBot.exe`.
- The user does not need to install Python.

## Build

Run on a Windows machine:

```text
build_windows_portable.bat
```

The finished portable app is created here:

```text
dist_portable\SPXBot
```

Give the whole `SPXBot` folder to the user.

## Start

The user starts:

```text
Start SPXBot.bat
```

The app opens the browser UI:

```text
http://127.0.0.1:8765
```

## Notes

This is usually the easiest no-certificate path for private use.

For public distribution, a signed installer is still the professional route.
