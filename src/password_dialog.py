"""
Password dialog functionality for Selfspy
"""

import getpass
from typing import Callable, Optional

from rich.prompt import Prompt


def get_password(
    verify: Optional[Callable[[str], bool]] = None,
    message: Optional[str] = None,
    force_save: bool = False,
) -> str:
    """Get password using Rich prompt"""
    for _ in range(3):
        pw = Prompt.ask(message or "Password", password=True, show_default=False)
        if not verify or verify(pw):
            break
    else:
        raise ValueError("Password verification failed")

    if (
        force_save
        or Prompt.ask(
            "Save password to keyring?", choices=["y", "n"], default="n"
        ).lower()
        == "y"
    ):
        set_keyring_password(pw)

    return pw


def set_keyring_password(password: str) -> None:
    """Store password in system keyring"""
    try:
        import keyring

        username = getpass.getuser()
        keyring.set_password("Selfspy", username, password)
    except ImportError:
        print("Unable to save password to keyring (library not found)")
    except Exception as e:
        print(f"Unable to save password to keyring: {e}")


if __name__ == "__main__":
    print(get_password())
