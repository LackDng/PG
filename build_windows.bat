@echo off
cd /d "%~dp0"

echo ============================================
echo   BUILD KARAOKE MANAGER - WINDOWS EXE
echo ============================================
echo.

:: Kiem tra Python
python --version > nul 2>&1
if errorlevel 1 (
    echo [LOI] Python chua duoc cai dat hoac chua them vao PATH.
    echo Tai Python tai: https://python.org/downloads/
    pause
    exit /b 1
)

echo [1/5] Cai dat cac thu vien Python...
:: Xoa cac folder bi hong (bat dau bang ~) truoc khi cai dat
for /d %%d in ("%LOCALAPPDATA%\Programs\Python\Python*\Lib\site-packages\~*") do (
    echo   Xoa folder bi hong: %%d
    rd /s /q "%%d" 2>nul
)
pip install -r requirements.txt pyinstaller --quiet
if errorlevel 1 (
    echo [LOI] Cai dat that bai.
    pause
    exit /b 1
)

echo [2/5] Thu thap static files...
cd karaoke_app
python manage.py collectstatic --noinput --clear -v 0
if errorlevel 1 (
    echo [LOI] collectstatic that bai.
    cd ..
    pause
    exit /b 1
)
cd ..

echo [3/5] Build exe bang PyInstaller...
pyinstaller karaoke.spec --clean --noconfirm
if errorlevel 1 (
    echo [LOI] PyInstaller that bai.
    pause
    exit /b 1
)

echo [4/5] Kiem tra ket qua build...
if exist "dist\KaraokeManager\KaraokeManager.exe" (
    echo [OK] File exe da duoc tao: dist\KaraokeManager\KaraokeManager.exe
) else (
    echo [LOI] Khong tim thay file exe.
    pause
    exit /b 1
)

echo [5/5] Nen thanh ZIP...
powershell Compress-Archive -Path "dist\KaraokeManager" -DestinationPath "dist\KaraokeManager_Windows.zip" -Force
echo [OK] Da tao: dist\KaraokeManager_Windows.zip

echo.
echo ============================================
echo   BUILD THANH CONG!
echo ============================================
echo.
echo Cac buoc tiep theo:
echo   - Dung luon: chay dist\KaraokeManager\KaraokeManager.exe
echo   - Tao file cai dat .exe: chay installer.iss bang Inno Setup
echo   - Chia se ZIP: dist\KaraokeManager_Windows.zip
echo.
echo Dang nhap lan dau: admin / admin123
echo.
pause
