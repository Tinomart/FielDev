@echo off
rem fieldev.cmd: runs FielDev.exe from a command line, so that a batch file or a build script has its output and its exit code:
rem     fieldev run bracket_maker.fieldevapp --Wall_thickness 2.5
rem     fieldev export tool.py -o tool.fieldevapp
rem     fieldev info tool.fieldevapp
rem (cmd.exe waits for a program that is run from a batch file, which it does not do for one typed at its prompt.)
"%~dp0FielDev.exe" %*
exit /b %ERRORLEVEL%
