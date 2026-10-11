# Steganography Tool

A Windows desktop app for hiding files or messages inside images, with optional password protection.

## Download

Download `BuryIt.exe` from the latest release in the repository's **Releases** section. The standalone app runs without a separate Python installation.

## Use the app

1. Choose **Hide data** or **Recover data**.
2. Select a PNG, JPEG, or BMP image. Recovery requires the original PNG that contains the hidden data.
3. To hide data, select a file or write a message. The app checks the carrier image capacity.
4. Optionally enable AES-256 password protection. Enter the password twice and keep it somewhere safe.
5. Review your choices and save the output PNG.

When recovering data, BuryIt detects whether the content is password protected. It prompts for a password only when one is required. Recovered messages can be copied; recovered files can be saved.

The progress screen reports the current operation while data is prepared, encrypted, embedded, and saved. If an operation fails, the app returns to the previous step and displays the error.

## Security and compatibility

Password-protected content uses AES-256-GCM. A key is derived from the UTF-8 password with scrypt (`N=32768`, `r=8`, `p=1`). Every operation uses a random 16-byte salt and 12-byte nonce. The GCM authentication tag detects incorrect passwords and tampering. The password is never stored in the image; if it is lost, the protected content cannot be recovered.

The app hides data in the least significant bits of RGB channels and preserves alpha. The legacy `STEGTR01` format remains supported alongside encrypted `STEGTR02` images. SHA-256 checks payload integrity.

The output is a lossless PNG. Do not resize it or convert it to JPEG, since those changes can destroy the hidden data. Share the original PNG file. Hidden files are saved as data and are never executed by the app.

## Build from source

Requirements: Python 3.10 or later and an internet connection for the initial package installation.

On Windows, double-click `Build-and-Run.cmd`, or run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build-pyqt.ps1
```

The script installs dependencies in `.venv`, runs the test suite, and builds `dist/BuryIt.exe`. To run from source after installation, use `run-pyqt.ps1`.

## Run tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The older C# implementation is retained in `Program.cs` and `build.ps1`.
