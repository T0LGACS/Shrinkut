@echo off
rem Yeni surumu yayinlar: degisiklikleri GitHub'a gonderir, .exe'yi GitHub kendisi derler.
rem Uygulamayi kullananlar acilista "Guncelle" dugmesini gorur.
cd /d "%~dp0"
git describe --tags --abbrev=0 2>nul && echo ^(yukaridaki son yayinlanan surum^)
set /p SURUM=Yeni surum numarasi (or. 1.0.1):
echo %SURUM%| findstr /r "^[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*$" >nul || (echo Gecersiz surum. Ornek: 1.0.1 & pause & exit /b 1)

git add -A
git commit -m "Surum %SURUM%" || echo (yeni degisiklik yok, sadece surum etiketi atiliyor)
git tag v%SURUM% || (echo Bu surum zaten yayinlanmis, daha buyuk bir numara ver. & pause & exit /b 1)
git push && git push origin v%SURUM% || (echo GitHub'a gonderilemedi. & pause & exit /b 1)

echo.
echo Gonderildi! GitHub .exe'yi 3-4 dakikada derleyip yayinlayacak.
pause
