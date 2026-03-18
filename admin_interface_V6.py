from tkinter import Tk, Label, Button, Frame, Entry, messagebox
from gui_helpers_V6 import set_view, fetch_font_settings


class Admin_Interface:
    """
    Provides the administrator login screen and top-level navigation interface,
    giving access to the Admin Console and Casino Interface.
    Automatically creates the database if it does not already exist.
    """

    def __init__(self):
        """
        Initialises the Admin Interface window and navigates to either the
        password check or the main admin menu depending on whether the
        administrator is already authenticated.
        """
        self.interface_root = Tk()

        self.interface_root.title("One More Time Casino - Administrator Interface")

        from database_management_and_logging_V6 import DatabaseManagement, DB_FILE

        self.dbm = DatabaseManagement()
        self.DB_FILE = DB_FILE

        if not self.dbm.check_database_exists():
            self.dbm.create_database()

        self.styles = fetch_font_settings(self.interface_root)

        self.main_frame = Frame(self.interface_root)
        self.main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        self.current_section_frame = None

        set_view(self, self.administrative_check)

        self.interface_root.mainloop()

    def administrative_check(self, frame):
        """
        Renders a password entry form for authentication.
        On a correct password, navigates to the main admin interface.
        On an incorrect password, displays an error and clears the entry field.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        Label(
            frame, text="Enter Administrator Password:", font=self.styles["text"]
        ).pack(pady=5)

        password_entry = Entry(frame, show="*", font=self.styles["text"])
        password_entry.pack(pady=5)

        def submit():
            """
            Reads the password entry field and verifies it against the stored
            administrator password hash. Navigates to the interface on success
            or shows an error dialog on failure.
            """
            password = password_entry.get()
            result = self.dbm.admin_password_check(password)

            if result.get("found") and result.get("verified"):
                set_view(self, self.interface_init)
            else:
                messagebox.showerror("Error", "Incorrect password")
                password_entry.delete(0, "end")

        Button(frame, text="Submit", font=self.styles["button"], command=submit).pack(
            pady=10
        )

    def interface_init(self, frame):
        """
        Renders the main administrator navigation menu with options to access
        the Admin Console, the Casino Interface, or exit the application.
        Also logs the administrator login event to the database.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        Label(frame, text="Welcome Administrator", font=self.styles["heading"]).pack(
            pady=20
        )

        self.dbm.admin_logged_in()

        buttons = [
            ("Access Admin Console", self.admin_console),
            ("Access Casino", self.access_casino),
            ("Exit", self.interface_root.destroy),
        ]

        for text, command in buttons:
            Button(
                frame, text=text, font=self.styles["button"], width=30, command=command
            ).pack(pady=3)

    def admin_console(self):
        """
        Opens the Admin Console window by instantiating the Admin_Console class
        from admin_console_V6.
        """
        from admin_console_V6 import Admin_Console

        Admin_Console()

    def access_casino(self):
        """
        Opens the Casino Interface in administrator mode by instantiating
        Casino_Interface with administrator=True from casino_interface_V6.
        """
        from casino_interface_V6 import Casino_Interface

        self.interface_root.destroy()

        Casino_Interface(True)


if __name__ == "__main__":
    Admin_Interface()
