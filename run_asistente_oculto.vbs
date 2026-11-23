Set WshShell = CreateObject("WScript.Shell")
strCurrentDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strCurrentDir
WshShell.Run """" & strCurrentDir & "\.venv\Scripts\pythonw.exe"" run_asistente.py", 0, False
