Option Explicit

' Launch the Social Toolkit GUI without showing a terminal window.
Dim shell, fso, projectRoot, script, launcher

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

projectRoot = fso.GetParentFolderName(WScript.ScriptFullName)
script = fso.BuildPath(projectRoot, "tools\social_toolkit_gui.py")

launcher = shell.ExpandEnvironmentStrings("%LOCALAPPDATA%\Programs\Python\Launcher\pyw.exe")
If Not fso.FileExists(launcher) Then
    launcher = "pyw.exe"
End If

shell.CurrentDirectory = projectRoot
shell.Run """" & launcher & """ """ & script & """", 0, False
