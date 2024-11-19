"""
Password dialog functionality for Selfspy
"""

import sys
import getpass
from typing import Optional, Callable
import tkinter as tk
from tkinter import simpledialog

def get_password(verify: Optional[Callable[[str], bool]] = None, 
                message: Optional[str] = None) -> str:
    """Get password from user through GUI or terminal"""
    
    if verify:
        pw = get_keyring_password(verify)
        if pw is not None:
            return pw
    
    return get_user_password(verify, message)

def get_user_password(verify: Optional[Callable[[str], bool]] = None,
                     message: Optional[str] = None,
                     force_save: bool = False) -> str:
    """Get password from user input"""
    
    if sys.stdin.isatty():
        return get_tty_password(verify, message, force_save)
    else:
        return get_tk_password(verify, message, force_save)

def get_keyring_password(verify: Callable[[str], bool],
                        message: Optional[str] = None) -> Optional[str]:
    """Try to get password from system keyring"""
    try:
        import keyring
        username = getpass.getuser()
        pw = keyring.get_password('Selfspy', username)
        
        if pw is not None:
            if verify(pw):
                return pw
            print('Stored keyring password is invalid.')
            pw = get_user_password(verify, message, force_save=True)
            return pw
            
    except ImportError:
        print('keyring library not found')
    
    return None

def set_keyring_password(password: str) -> None:
    """Store password in system keyring"""
    try:
        import keyring
        username = getpass.getuser()
        keyring.set_password('Selfspy', username, password)
    except ImportError:
        print('Unable to save password to keyring (library not found)')
    except Exception as e:
        print(f'Unable to save password to keyring: {e}')

def get_tty_password(verify: Optional[Callable[[str], bool]] = None,
                    message: Optional[str] = None,
                    force_save: bool = False) -> str:
    """Get password from terminal"""
    
    for _ in range(3):
        pw = getpass.getpass(message or 'Password: ')
        if not verify or verify(pw):
            break
    else:
        print('Password verification failed')
        sys.exit(1)

    if force_save or input("Save password to keyring? [y/N]: ").lower() == 'y':
        set_keyring_password(pw)

    return pw

def get_tk_password(verify: Optional[Callable[[str], bool]] = None,
                   message: Optional[str] = None,
                   force_save: bool = False) -> str:
    """Get password using tkinter dialog"""
    
    root = tk.Tk()
    root.withdraw()
    
    while True:
        dialog = PasswordDialog(
            title='Selfspy Password',
            prompt=message or 'Password:',
            parent=root
        )
        
        pw, save = dialog.result
        
        if pw is None:
            return ""
            
        if not verify or verify(pw):
            break
    
    if save or force_save:
        set_keyring_password(pw)
        
    return pw

class PasswordDialog(simpledialog.Dialog):
    """Custom password dialog with save option"""
    
    def __init__(self, title: str, prompt: str, parent: tk.Tk):
        self.prompt = prompt
        super().__init__(parent, title)

    def body(self, master: tk.Frame) -> tk.Entry:
        """Create dialog body"""
        tk.Label(master, text=self.prompt).grid(row=0, sticky=tk.W)
        
        self.password_entry = tk.Entry(master, show='*')
        self.password_entry.grid(row=0, column=1)
        
        self.save_var = tk.BooleanVar()
        tk.Checkbutton(master, 
                      text="Save to keyring",
                      variable=self.save_var).grid(row=1, columnspan=2, sticky=tk.W)
        
        return self.password_entry

    def apply(self) -> None:
        """Store results when OK is clicked"""
        self.result = (self.password_entry.get(), self.save_var.get())

if __name__ == '__main__':
    print(get_password())