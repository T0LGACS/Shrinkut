@echo off
rem Bilgisayarda deneme amacli derleme. Yayinlamak icin yayinla.bat kullan.
cd /d "%~dp0"
echo [1/3] Gerekli paketler kuruluyor...
pip install -r requirements.txt

echo.
echo [2/3] .exe olusturuluyor (1-2 dakika surebilir)...
pyinstaller --noconfirm --onefile --windowed --name "Shrinkut" --icon icon.ico --version-file version_info.txt ^
  --add-data "icon.ico;." --collect-data customtkinter --collect-all tkinterdnd2 ^
  --collect-binaries imageio_ffmpeg app.py

echo.
echo [3/3] Tamam! dist\Shrinkut.exe hazir.
pause
