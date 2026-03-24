@echo off
echo Building Huawei Cloud Pricing Tool executable...
echo.
pyinstaller --onefile --windowed --add-data "app/data;data" --add-data "templates;templates" app/huawei_pricing_app.py
echo.
if exist dist\huawei_pricing_app.exe (
    echo Build complete! Executable located in dist\ folder.
) else (
    echo Build failed. Please check the error messages above.
)
pause