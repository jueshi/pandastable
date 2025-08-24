# Tesseract OCR Installation Guide (Windows)

This guide explains how to install the Tesseract OCR engine and the Python `pytesseract` package used by the Image Browser example.

## 1) Install the Tesseract OCR engine

- Download the Windows installer from the official repository:
  - https://github.com/tesseract-ocr/tesseract
  - Direct Windows builds are typically linked in the README (UB Mannheim builds are commonly used).
- Run the installer and accept defaults. The common install path is:
  - `C:\Program Files\Tesseract-OCR\tesseract.exe`

Optional: Add the install folder to your PATH so it’s globally available:
- System Properties → Environment Variables → Edit the `Path` (user or system) → Add `C:\Program Files\Tesseract-OCR` → OK.

## 2) Ensure `pip` is available for your Python

If your Python doesn’t have `pip` yet, bootstrap it:

```powershell
& "C:\Users\<YOU>\AppData\Local\Programs\Python\Python313\python.exe" -m ensurepip --upgrade
```

Then upgrade `pip` (optional):

```powershell
& "C:\Users\<YOU>\AppData\Local\Programs\Python\Python313\python.exe" -m pip install --upgrade pip
```

Replace `<YOU>` with your Windows username and the Python version/path with the one you’re actually using.

## 3) Install the Python package `pytesseract`

Install `pytesseract` into the same Python that runs the app:

```powershell
& "C:\Users\<YOU>\AppData\Local\Programs\Python\Python313\python.exe" -m pip install --user pytesseract pillow
```

Verify the installation:

```powershell
& "C:\Users\<YOU>\AppData\Local\Programs\Python\Python313\python.exe" -c "import sys, pytesseract; print('OK', pytesseract.__version__, sys.executable)"
```

If you see `OK <version> <path-to-python>`, the package import works.

## 4) Configure the app to find `tesseract.exe` (if needed)

If the app prompts for Tesseract or can’t find it, set the path once in your app code (e.g., in your Image Browser class `__init__`):

```python
self.tesseract_cmd_path = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
```

The OCR code will use `self.tesseract_cmd_path` first and remember it for the current session.

## 5) Common issues

- "No module named `pytesseract`": install it in the exact interpreter used to run the app (see step 3). Using a different Python will not work.
- PowerShell error about `-m` being an unexpected token: put `&` before the quoted python path, e.g. `& "<path-to-python>" -m pip ...`.
- Pytesseract installed but Tesseract not found: ensure the engine is installed (step 1) and that the path is either on `PATH` or set via `self.tesseract_cmd_path`.

## 6) Quick checklist

- [ ] Install Tesseract OCR engine (binary)
- [ ] Ensure `pip` exists for your Python
- [ ] Install `pytesseract` (and `Pillow`)
- [ ] Verify import works
- [ ] Optionally set `self.tesseract_cmd_path` in the app
