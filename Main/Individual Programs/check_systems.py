import os
import hashlib
import hmac
import binascii
from tkinter import Frame, Toplevel, messagebox
from gui_helpers import (
    fetch_text_styles,
    CS,
    create_window,
    preset_label,
    preset_entry,
    preset_button,
)

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


PASSWORD_CRITERIA = [
    # (description_string, rule_function) pair
    (
        "At least 8 characters",
        lambda pwd: len(pwd) >= 8,
    ),
    (
        "At least one uppercase letter (A–Z)",
        lambda pwd: any(char.isupper() for char in pwd),
    ),
    (
        "At least one lowercase letter (a–z)",
        lambda pwd: any(char.islower() for char in pwd),
    ),
    (
        "At least one digit (0–9)",
        lambda pwd: any(char.isdigit() for char in pwd),
    ),
    (
        "At least one special character (!@#$%^&* etc.)",
        lambda pwd: any(not char.isalnum() for char in pwd),
    ),
]


def validate_password(password):
    """
    Checks a plaintext password against every rule in PASSWORD_CRITERIA.

    Args:
        password (str): The password to validate.

    Returns:
        tuple[bool, list[str]]:
            - passed (bool): True only when every rule is satisfied.
            - failures (list[str]): Descriptions of rules that were not met.
              Empty when passed is True.
    """
    failures = [
        description for description, rule in PASSWORD_CRITERIA if not rule(password)
    ]
    return (len(failures) == 0), failures


def passwords_confirmation(frame, root):
    """
    Opens a modal Toplevel dialog prompting the user to enter and confirm a
    new password. The dialog cannot be closed through the window manager's
    close button; the user must submit or cancel explicitly.

    A requirements checklist is displayed beneath the first entry field
    and updates on every keystroke. Each rule is drawn from PASSWORD_CRITERIA
    so the displayed criteria always match the enforced criteria. The Submit
    button is kept disabled until all rules pass and both fields match.

    Args:
        frame: The parent widget used to position the Toplevel window.
        root: The root Tk window, used for font settings and blocking through
              wait_window().

    Returns:
        dict: A dictionary with two keys:
              - 'confirmed' (bool): True if the user submitted a password that
                satisfies PASSWORD_CRITERIA and whose confirmation field matches.
              - 'password' (str or None): The confirmed password string, or
                None if the dialog was cancelled or validation failed.
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
    ).pack(pady=(10, 2))

    password_entry_1 = preset_entry(password_window, show="*", width=30)
    password_entry_1.pack(pady=(0, 4))

    rule_labels = []
    for description, _ in PASSWORD_CRITERIA:
        label = preset_label(
            password_window,
            text=f"Needs: {description}",
            fg=CS["error"],
            font=styles["emphasis"],
            justify="center",
        )
        label.pack(pady=1)
        rule_labels.append(label)

    preset_label(
        password_window,
        text="Confirm password:",
    ).pack(pady=(4, 2))

    password_entry_2 = preset_entry(password_window, show="*", width=30)
    password_entry_2.pack(pady=(0, 6))

    button_frame = Frame(password_window)
    button_frame.pack(pady=10)

    submit_button = preset_button(
        button_frame,
        text="Submit",
        state="disabled",
    )
    submit_button.pack(side="left", padx=5)

    def refresh_checklist(*_):
        """
        Called on every keystroke in either entry field.

        Re-evaluates PASSWORD_CRITERIA against the current first-field value,
        updates each rule label's text and colour, and enables or disables
        the Submit button depending on whether all rules pass and both fields
        are identical.
        """
        candidate = password_entry_1.get()
        _, failures = validate_password(candidate)
        failure_set = set(failures)

        for label, (description, _) in zip(rule_labels, PASSWORD_CRITERIA):
            if description in failure_set:
                label.config(text=f"Needs: {description}", fg=CS["error"])
            else:
                label.config(text=f"Requirement fulfilled.", fg=CS["correct"])

        all_rules_pass = len(failures) == 0
        passwords_match = candidate == password_entry_2.get() and bool(candidate)

        submit_button.config(
            state="normal" if (all_rules_pass and passwords_match) else "disabled"
        )

    password_entry_1.bind("<KeyRelease>", refresh_checklist)
    password_entry_2.bind("<KeyRelease>", refresh_checklist)

    def validate_passwords():
        """
        Final check on Submit then updates the shared password dict
        and closes the dialog.
        """
        password_1 = password_entry_1.get().strip()
        password_2 = password_entry_2.get().strip()

        passed, failures = validate_password(password_1)

        if not password_1:
            messagebox.showerror(
                "Error",
                "Password cannot be empty.",
                parent=password_window,
            )
            return

        if not passed:
            messagebox.showerror(
                "Password Requirements Not Met",
                "Your password does not meet the following requirements:\n\n"
                + "\n".join(f"• {f}" for f in failures),
                parent=password_window,
            )
            return

        if password_1 != password_2:
            messagebox.showerror(
                "Error",
                "Passwords do not match. Please try again.",
                parent=password_window,
            )
            return

        password["confirmed"] = True
        password["password"] = password_1
        password_window.destroy()

    submit_button.config(command=validate_passwords)

    def cancel_password():
        password_window.destroy()

    preset_button(button_frame, text="Cancel", command=cancel_password).pack(
        side="left", padx=5
    )

    root.wait_window(password_window)

    return password
