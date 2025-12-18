Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "f:\opensource\marine_ranching\observationnetwork"
WshShell.Run "pythonw thingsboard_sync_service.py --interval 300", 0, False
