import os
import sys
import ctypes
import win32service
import win32serviceutil
import win32event
import servicemanager

# Import your assistant functionality from Assistant.py
from Assistant import speak
from Alpha import Brain

class AssistantService(win32serviceutil.ServiceFramework):
    _svc_name_ = "AlphaAssistant"
    _svc_display_name_ = "Alpha Assistant Service"
    _svc_description_ = "This service runs the Alpha Assistant."

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.brain = None

    def SvcDoRun(self):
        self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
        try:
            self.brain = Brain(intelligence=0.6)
            self.ReportServiceStatus(win32service.SERVICE_RUNNING)
            self.brain.run_assistant()
        except Exception as e:
            servicemanager.LogErrorMsg(f"Error starting service: {str(e)}")
            self.ReportServiceStatus(win32service.SERVICE_STOPPED)
            raise

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        if self.brain:
            self.brain.shutdown()
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)
        win32event.SetEvent(self.stop_event)

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    # Get the path to the script and the Python executable
    script = os.path.abspath(sys.argv[0])
    params = ' '.join([os.path.abspath(arg) for arg in sys.argv[1:]])
    
    # Create the command to run the script as admin
    cmd = f'"{sys.executable}" "{script}" {params}'
    
    # Execute the command with elevated privileges
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, cmd, None, 1)

if __name__ == '__main__':
    if not is_admin():
        run_as_admin()
    else:
        if len(sys.argv) == 1:
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(AssistantService)
            servicemanager.StartServiceCtrlDispatcher()
        else:
            win32serviceutil.HandleCommandLine(AssistantService)
