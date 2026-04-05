import sys
import os
from tkinter import Tk, messagebox, filedialog
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from datetime import datetime
from gui_helpers import  CS, create_window, preset_label, preset_button, set_view


class EncryptionSoftware:
    """
    GUI tool for hybrid RSA/AES file encryption and decryption. Used by
    administrators to secure database files or other data.
    """

    def __init__(self):
        """
        Initialises the root window, applies GUI styles, logs the system access
        event via DatabaseManagement, sets the AES key placeholder to None and
        starts the main interface.
        """
        self.window_bg = CS["admin"]
        self.enc_soft_root = Tk()
        self.main_frame, self.styles = create_window(
            self.enc_soft_root,
            "One Less Time Casino - Encryption Software",
            self.window_bg,
            is_main_frame=True,
        )
        self.enc_soft_root.protocol(
            "WM_DELETE_WINDOW", lambda: (self.enc_soft_root.quit(), sys.exit(0))
        )

        try:
            from database_management_and_logging import DatabaseManagement, DB_PATH
            
            self.dbm = DatabaseManagement(DB_PATH)
            self.dbm.admin_accessed_system("Encryption Software")
        except Exception:
            pass

        self.aes_key = None

        self.current_section_frame = None

        set_view(self, self.create_main_menu)

        self.enc_soft_root.mainloop()

    def create_main_menu(self, frame):
        """
        Builds the main menu interface with buttons for all available
        operations: generating an RSA keypair, generating and encrypting an AES
        key, loading an encrypted AES key, encrypting a file, decrypting a
        file and exiting.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        preset_label(
            frame,
            text="Encryption Software",
            font=self.styles["heading"],
        ).pack(pady=10)

        buttons = [
            ("Generate RSA Keypair", self.generate_rsa_keys),
            ("Generate & Encrypt AES Key", self.generate_encrypted_aes_key),
            ("Load Encrypted AES Key", self.load_rsa_aes_key),
            ("Encrypt File", self.encrypt_file),
            ("Decrypt File", self.decrypt_file),
            ("Exit", self.enc_soft_root.destroy),
        ]

        for text, command in buttons:
            preset_button(
                frame,
                text=text,
                width=40,
                command=command,
            ).pack(pady=5)

    def generate_rsa_keys(self):
        """
        Generates a 2048-bit RSA keypair and saves both the private and public
        keys as PEM files to a user-selected directory. Filenames include a
        timestamp in DD-Month-YYYY format. Displays a success message with the
        saved file paths, or an error message if generation or saving fails.
        """
        save_dir = filedialog.askdirectory(title="Select folder to save RSA keys")
        if not save_dir:
            return

        try:
            key = RSA.generate(2048)

            private_key = key.export_key()

            public_key = key.publickey().export_key()

            timestamp = datetime.now().strftime("%d-%B-%Y")

            private_path = os.path.join(save_dir, f"private_key_{timestamp}.pem")

            public_path = os.path.join(save_dir, f"public_key_{timestamp}.pem")

            with open(private_path, "wb") as file:
                file.write(private_key)

            with open(public_path, "wb") as file:
                file.write(public_key)

            messagebox.showinfo(
                "Success",
                f"RSA keys generated and saved:\n{private_path}\n{public_path}",
            )

        except Exception as error:
            messagebox.showerror("Error", f"Failed to generate RSA keys: {error}")

    def generate_encrypted_aes_key(self):
        """
        Generates a random 256-bit AES key, encrypts it using a user-selected
        RSA public key via PKCS1-OAEP and saves the encrypted result as a
        binary file to a user-selected directory. The filename includes a
        timestamp in DD-Month-YYYY format. Displays a success message with the
        saved file path, or an error message on failure.
        """
        rsa_pub_file = filedialog.askopenfilename(
            title="Select RSA Public Key",
            filetypes=[("PEM files", "*.pem"), ("All files", "*.*")],
        )

        if not rsa_pub_file:
            return

        save_dir = filedialog.askdirectory(
            title="Select folder to save encrypted AES key"
        )
        if not save_dir:
            return

        try:
            aes_key = get_random_bytes(32)

            with open(rsa_pub_file, "rb") as file:
                public_key = RSA.import_key(file.read())

            cipher_rsa = PKCS1_OAEP.new(public_key)

            encrypted_aes = cipher_rsa.encrypt(aes_key)

            timestamp = datetime.now().strftime("%d-%B-%Y")

            save_path = os.path.join(save_dir, f"aes_key_{timestamp}.bin")

            with open(save_path, "wb") as file:
                file.write(encrypted_aes)

            messagebox.showinfo("Success", f"Encrypted AES key saved to:\n{save_path}")

        except Exception as error:
            messagebox.showerror(
                "Error", f"Failed to generate/encrypt AES key: {error}"
            )

    def load_rsa_aes_key(self):
        """
        Prompts the user to select an RSA private key file and an encrypted AES
        key file and then decrypts the AES key using PKCS1-OAEP and stores it in
        memory as self.aes_key. The loaded key is used for subsequent encrypt
        and decrypt operations. Displays a success message on completion, or an
        error message if decryption fails.
        """
        rsa_private_file = filedialog.askopenfilename(
            title="Select RSA Private Key",
            filetypes=[("PEM files", "*.pem"), ("All files", "*.*")],
        )

        if not rsa_private_file:
            return

        encrypted_aes_file = filedialog.askopenfilename(
            title="Select Encrypted AES Key",
            filetypes=[("Binary files", "*.bin"), ("All files", "*.*")],
        )
        if not encrypted_aes_file:
            return

        try:
            with open(rsa_private_file, "rb") as file:
                private_key = RSA.import_key(file.read())

            with open(encrypted_aes_file, "rb") as file:
                encrypted_aes = file.read()

            cipher_rsa = PKCS1_OAEP.new(private_key)

            self.aes_key = cipher_rsa.decrypt(encrypted_aes)

            messagebox.showinfo("Success", "AES key loaded successfully.")

        except Exception as error:
            messagebox.showerror("Error", f"Failed to load AES key: {error}")

    def encrypt_file(self):
        """
        Encrypts a user-selected file using the currently loaded AES key in EAX
        mode. The encrypted output is saved to the same location with a .enc
        extension appended. The file contains the nonce, authentication tag and
        ciphertext concatenated in that order. Displays a warning if no AES key
        is loaded, a success message with the output path on completion, or an
        error message on failure.
        """
        if not self.aes_key:
            messagebox.showwarning("Warning", "Please load an AES key first.")
            return

        file_path = filedialog.askopenfilename(
            title="Select database to encrypt",
            filetypes=[("Database files", "*.db"), ("All files", "*.*")],
        )

        if not file_path:
            return

        try:
            with open(file_path, "rb") as file:
                data = file.read()

            cipher = AES.new(self.aes_key, AES.MODE_EAX)

            ciphertext, tag = cipher.encrypt_and_digest(data)

            save_path = file_path + ".enc"

            with open(save_path, "wb") as file:
                file.write(cipher.nonce)
                file.write(tag)
                file.write(ciphertext)

            messagebox.showinfo(
                "Success", f"Database encrypted and saved to:\n{save_path}"
            )

        except Exception as error:
            messagebox.showerror("Error", f"Encryption failed: {error}")

    def decrypt_file(self):
        """
        Decrypts a user-selected .enc file using the currently loaded AES key
        in EAX mode. Reads the nonce, authentication tag and ciphertext from
        the file, verifies the authentication tag and writes the decrypted
        plaintext to disk. The output path is the input path with the .enc
        extension removed, or with .dec appended if the file does not end in
        .enc. Displays a warning if no AES key is loaded, a success message
        with the output path on completion, or an error message if decryption
        or tag verification fails.
        """
        if not self.aes_key:
            messagebox.showwarning("Warning", "Please load an AES key first.")
            return

        file_path = filedialog.askopenfilename(
            title="Select encrypted database",
            filetypes=[("Encrypted files", "*.enc"), ("All files", "*.*")],
        )

        if not file_path:
            return

        try:
            with open(file_path, "rb") as file:
                nonce = file.read(16)
                tag = file.read(16)
                ciphertext = file.read()

            cipher = AES.new(self.aes_key, AES.MODE_EAX, nonce=nonce)

            data = cipher.decrypt_and_verify(ciphertext, tag)

            save_path = (
                file_path[:-4] if file_path.endswith(".enc") else file_path + ".dec"
            )

            with open(save_path, "wb") as file:
                file.write(data)

            messagebox.showinfo(
                "Success", f"Database decrypted and saved to:\n{save_path}"
            )

        except Exception as error:
            messagebox.showerror("Error", f"Decryption failed: {error}")


if __name__ == "__main__":
    EncryptionSoftware()
