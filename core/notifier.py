import subprocess
import logging

def show_notification(title, message):
    """
    Displays a Windows Toast Notification using PowerShell using standard libraries only.
    This avoids external dependencies like 'win10toast' or complex ctypes implementations.
    """
    try:
        # PowerShell script to create a toast notification
        # This uses the Windows Runtime API available in Windows 10/11
        ps_script = f"""
        $ErrorActionPreference = 'Stop'
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
        $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
        $textNodes = $template.GetElementsByTagName("text")
        $textNodes.Item(0).AppendChild($template.CreateTextNode("{title}")) > $null
        $textNodes.Item(1).AppendChild($template.CreateTextNode("{message}")) > $null
        $notification = [Windows.UI.Notifications.ToastNotification]::new($template)
        $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("VRPhoto Checker")
        $notifier.Show($notification)
        """
        
        # Execute PowerShell script
        # CREATE_NO_WINDOW is used to prevent the PowerShell window from popping up
        subprocess.run(
            ["powershell", "-Command", ps_script], 
            capture_output=True, 
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        logging.info(f"Notification sent: {title} - {message}")
        
    except Exception as e:
        logging.error(f"Failed to send notification: {e}")
