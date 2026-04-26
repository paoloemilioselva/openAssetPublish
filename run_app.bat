@ECHO OFF
SET PROJECT_ROOT=%~dp0
cd /d %PROJECT_ROOT%

:: Call the USD environment setup
:: Use /c to run the command and then return to the current batch file if needed, 
:: but here we just want to run python main.py in that env.
:: Since the user's batch ends with 'cmd.exe', we might need to bypass that 
:: or provide our own logic.

:: We will mimic the environment variables from the user's batch file 
:: to ensure python main.py runs correctly without hanging at a cmd prompt.

SET USDROOT=C:\dev\usd-26.03
SET RMANTREE=C:\Program Files\Pixar\RenderManProServer-26.3

SET RMAN_SHADERPATH=%RMANTREE%\lib\shaders;%USDROOT%\plugin\usd\resources\shaders
SET RMAN_RIXPLUGINPATH=%RMANTREE%\lib\plugins
SET RMAN_TEXTUREPATH=%RMANTREE%\lib\textures:%RMANTREE%\lib\plugins:%USDROOT%\plugin\usd
SET RMAN_DISPLAYPATH=%RMANTREE%\lib\plugins
SET RMAN_PROCEDURALPATH=%RMANTREE%\lib\plugins

SET PXR_PLUGINPATH_NAME=%USDROOT%;%USDROOT%\plugin\usd

SET PYTHONPATH=%USDROOT%\lib\python;%PYTHONPATH%

SET PATH=%USDROOT%\bin;%RMANTREE%\bin;%PATH%
SET PATH=%USDROOT%\lib;%RMANTREE%\lib;%PATH%

:: Now launch the app
python main.py
