import os
import hashlib
import hmac
import binascii
from tkinter import Entry, Label, Button, Frame, Toplevel, messagebox
from gui_helpers_V6 import fetch_text_styles, CS, create_window, preset_label, preset_entry, preset_button

PBKDF2_ITERATIONS = 200_000  # Iterations for password hashing (Password-Based Key Derivation Function 2).
SALT_BYTES = 16  # Number of random bytes for salt.


def hash_function(string):
    """
    Hashes a plaintext string using PBKDF2-HMAC-SHA256 with a randomly generated
    salt.

    Args:
        string (str): The plaintext string to hash.

    Returns:
        str: A '$'-delimited string in the format 'salt_hex$hash_hex', where
             both components are hexadecimal representations of their respective
             byte sequences.

    Raises:
        TypeError: If the input is not a string.
    """
    if not isinstance(string, str):
        raise TypeError("Input must be a string.")

    # Generate a random salt.
    salt = os.urandom(SALT_BYTES)

    # Derive the hash using PBKDF2-HMAC-SHA256.
    derived_key = hashlib.pbkdf2_hmac(
        "sha256", string.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )

    # Return the salt and hash joined by a '$' character.
    return f"{binascii.hexlify(salt).decode()}${binascii.hexlify(derived_key).decode()}"


def verify_hash(stored_string, input_string):
    """
    Verifies a plaintext string against a stored PBKDF2-HMAC-SHA256 hash.
    Uses a constant-time comparison to prevent timing attacks.

    Args:
        stored_string (str): The previously stored hash string in the format
                             'salt_hex$hash_hex' as produced by hash_function().
        input_string (str): The plaintext string to verify.

    Returns:
        bool: True if the input string matches the stored hash, False otherwise
              (including if the stored string is malformed).
    """
    try:
        salt_hex, hash_hex = stored_string.split("$")
    except ValueError:
        # The stored hash isn't in the expected format.
        return False

    salt = binascii.unhexlify(salt_hex)
    stored_hash = binascii.unhexlify(hash_hex)

    # Derive a hash using the same salt and parameters.
    input_hash = hashlib.pbkdf2_hmac(
        "sha256", input_string.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )

    return hmac.compare_digest(input_hash, stored_hash)


def passwords_confirmation(frame, root):
    """
    Opens a modal Toplevel dialog prompting the user to enter and confirm a
    new password. The dialog cannot be closed via the window manager's close
    button; the user must submit or cancel explicitly.

    Args:
        frame: The parent widget used to position the Toplevel window.
        root: The root Tk window, used for font settings and blocking via
              wait_window().

    Returns:
        dict: A dictionary with two keys:
              - 'confirmed' (bool): True if the user submitted matching
                non-empty passwords, False otherwise.
              - 'password' (str or None): The confirmed password string, or
                None if the dialog was cancelled or passwords did not match.
    """
    styles = fetch_text_styles(root)

    # Default return state.
    password = {"confirmed": False, "password": None}

    password_window = Toplevel(frame)
    create_window(password_window, "Set New Password", CS["pwd_prompt"])
    password_window.protocol("WM_DELETE_WINDOW", lambda: None)

    preset_label(
        password_window,
        text="Enter password:",
        font=styles["text"],
        bg=CS["pwd_prompt"],
    ).pack(pady=5)

    password_entry_1 = preset_entry(password_window, show="*", width=30)
    password_entry_1.pack(pady=5)

    preset_label(
        password_window,
        text="Confirm password:",
        font=styles["text"],
        bg=CS["pwd_prompt"],
    ).pack(pady=5)

    password_entry_2 = preset_entry(password_window, show="*", width=30)
    password_entry_2.pack(pady=5)

    def validate_passwords():
        """
        Validates that both password fields are non-empty and identical.
        On success, updates the shared password dict and closes the dialog.
        On failure, displays an error message inside the dialog.
        """
        password_1 = password_entry_1.get().strip()
        password_2 = password_entry_2.get().strip()

        if password_1 and password_1 == password_2:
            password["confirmed"] = True
            password["password"] = password_1
            password_window.destroy()
        else:
            messagebox.showerror(
                "Error",
                "Passwords do not match or are empty. Please try again.",
                parent=password_window,
            )

    def cancel_password():
        """
        Closes the password dialog without confirming, leaving the shared
        password dict in its default unconfirmed state.
        """
        password_window.destroy()

    button = Frame(password_window)
    button.pack(pady=10)

    preset_button(button, text="Submit", command=validate_passwords).pack(
        side="left", padx=5
    )

    preset_button(button, text="Cancel", command=cancel_password).pack(
        side="left", padx=5
    )

    root.wait_window(password_window)

    return password
