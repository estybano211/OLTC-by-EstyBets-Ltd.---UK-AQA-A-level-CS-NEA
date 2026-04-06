import sys
import os
from tkinter import (
    BOTH,
    BOTTOM,
    BooleanVar,
    Canvas,
    Checkbutton,
    END,
    Entry,
    Frame,
    filedialog,
    HORIZONTAL,
    IntVar,
    messagebox,
    Scale,
    Scrollbar,
    scrolledtext,
    simpledialog,
    Spinbox,
    StringVar,
    Tk,
    Toplevel,
    WORD,
    X,
)
from tkinter.ttk import Combobox, Treeview
import random
from search_sort_algorithms import bubble_sort, binary_search_by_id
from gui_helpers import (
    CS,
    create_window,
    preset_label,
    preset_button,
    preset_entry,
    set_view,
)


class BaseInterface:
    """
    Base class for all top-level Tkinter interface windows.
    Handles common setup tasks and defines the contract for subclasses.
      - Creates and configures the Tk root window.
      - Stores self.window_bg, self.styles, self.main_frame.
      - Instantiates self.dbm (DatabaseManagement).
      - Checks for and creates the database if absent.
      - Initialises self.current_section_frame to None.
      - Binds WM_DELETE_WINDOW to a safe quit handler.
      - Navigates to the first view via startup().
      - Starts the Tk mainloop.

    Subclasses must define:
      WINDOW_TITLE  (str or property) — the window title bar text.
      WINDOW_BG_KEY (str) — a key from the CS colour scheme dict.
      startup() — returns the view method to show on startup.

    Subclasses may override on_close() to customise the window-close
    behaviour (default: quit the mainloop and exit the process).
    """

    WINDOW_TITLE = ""
    WINDOW_BG_KEY = ""

    def startup(self):
        """
        Returns the view method that should be shown immediately after
        the window opens. Subclasses should override this method.

        Returns:
            callable: A bound method that accepts a Frame argument, or None if not overridden.
        """
        return None

    def __init__(self):
        """
        Builds the window, sets up shared state, navigates to the first
        view and starts the mainloop.

        Subclasses that need additional setup (e.g. CasinoInterface
        accepting constructor arguments) should do that work before
        calling super().__init__(), or override __init__ and call
        super().__init__() at the end once their own state is ready.
        """
        self.window_bg = CS[self.WINDOW_BG_KEY]

        self.interface_root = Tk()

        window_title = self.WINDOW_TITLE

        self.main_frame, self.styles = create_window(
            self.interface_root,
            window_title,
            self.window_bg,
            is_main_frame=True,
        )

        self.interface_root.protocol("WM_DELETE_WINDOW", self.on_close)

        from database_management_and_logging import DatabaseManagement, DB_PATH

        self.db_path = DB_PATH
        self.dbm = DatabaseManagement(self.db_path)

        if not self.dbm.check_database_exists():
            self.dbm.create_database()

        self.dbm.check_expired_guest_account()
        self.dbm.apply_daily_login_bonus()

        self.current_section_frame = None

        set_view(self, self.startup())

        self.interface_root.mainloop()

    def on_close(self):
        """
        Default window-close handler: stops the mainloop and exits the
        process. Subclasses may override this for custom behaviour.
        """
        self.interface_root.quit()
        sys.exit(0)


class AdminInterface(BaseInterface):
    """
    Administrator login screen and top-level navigation interface.
    Gives access to the Admin Console and the Casino Interface.

    Starts at the password check screen. On successful authentication,
    the administrator may open the console or access the casino.
    """

    WINDOW_TITLE = "One Less Time Casino - Administrator Interface"
    WINDOW_BG_KEY = "admin"

    def startup(self):
        return self.administrative_check

    def __init__(self):
        """
        Initialises the Admin Interface window and navigates to either the
        password check or the main admin menu depending on whether the
        administrator is already authenticated.
        """
        super().__init__()

    def administrative_check(self, frame):
        """
        Renders a password entry form for authentication.
        On a correct password, navigates to the main admin interface.
        On an incorrect password, displays an error and clears the entry field.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        preset_label(frame, text="Enter Administrator Password:").pack(pady=5)

        password_entry = preset_entry(frame, show="*")
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
                set_view(self, self.interface_menu)
            else:
                messagebox.showerror(
                    "Error", "Incorrect password", parent=self.interface_root
                )
                password_entry.delete(0, "end")

        preset_button(frame, text="Submit", command=submit).pack(pady=10)

    def interface_menu(self, frame):
        """
        Renders the main administrator navigation menu with options to access
        the Admin Console, the Casino Interface, or exit the application.
        Also logs the administrator login event to the database.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        preset_label(
            frame, text="Welcome Administrator", font=self.styles["heading"]
        ).pack(pady=20)

        self.dbm.admin_logged_in()

        buttons = [
            ("Access Admin Console", self.admin_console),
            ("Access Casino", self.access_casino),
            ("Exit", self.interface_root.destroy),
        ]

        for text, command in buttons:
            preset_button(frame, text=text, width=30, command=command).pack(pady=3)

    def admin_console(self):
        """
        Opens the Admin Console window by instantiating the AdminConsole class.
        """

        AdminConsole()

    def access_casino(self):
        """
        Opens the Casino Interface in administrator mode by instantiating
        CasinoInterface with administrator=True.
        """

        self.interface_root.destroy()

        CasinoInterface(True)


class AdminConsole(BaseInterface):
    """
    Administrator console providing access to password management,
    encryption software, database management and user management.
    Sensitive operations are gated behind a master password.
    """

    WINDOW_TITLE = "One Less Time Casino - Administrative Console"
    WINDOW_BG_KEY = "admin"
    MASTER_PASSWORD = "Master_Password"

    def startup(self):
        return self.show_console_menu

    def __init__(self):
        """
        Initialises the Admin Console window with the master password
        constant and then delegates to BaseInterface for standard setup.
        """
        super().__init__()

    def show_console_menu(self, frame):
        """
        Renders the main admin console menu with navigation buttons for all
        available administrative operations.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        preset_label(
            frame,
            text="Administrative Console",
            font=self.styles["heading"],
        ).pack(pady=(0, 20))

        buttons = [
            (
                "Change Administrative Password",
                lambda: set_view(self, self.change_admin_password),
            ),
            ("Access Encryption Software", self.encryption_software_access),
            (
                "Database Management",
                lambda: set_view(self, self.show_database_management),
            ),
            ("User Management", lambda: set_view(self, self.show_user_management)),
            ("Exit", self.interface_root.destroy),
        ]

        for text, command in buttons:
            preset_button(frame, text=text, width=30, command=command).pack(pady=5)

    def change_admin_password(self, frame):
        """
        Renders the admin password change flow. Requires master password
        verification before prompting for the current admin password and then
        uses passwords_confirmation to set a new one. Displays appropriate
        error or success dialogs at each stage and returns to the main menu
        on completion or cancellation.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        if not self.dbm.check_database_exists():
            messagebox.showwarning(
                "Warning",
                f"'{self.db_path}' does not exist.",
                parent=self.interface_root,
            )
            return
        if messagebox.askyesno(
            "Confirm password change",
            "Are you sure you want to change the administrative password to the system?",
            parent=self.interface_root,
        ):
            try:
                password = simpledialog.askstring(
                    "Verification",
                    "Please enter Master Password to continue:",
                    show="*",
                    parent=self.interface_root,
                )

                if password == self.MASTER_PASSWORD:
                    preset_label(
                        frame,
                        text="Enter Old Administrator Password:",
                        font=self.styles["heading"],
                    ).pack(pady=20)

                    password_entry = preset_entry(frame, show="*")
                    password_entry.pack(pady=5)

                    def submit():
                        """
                        Verifies the current admin password and then launches the
                        password confirmation dialog to capture and store the
                        new password. Returns to the main menu on success.
                        """
                        old_password = password_entry.get()
                        result = self.dbm.admin_password_check(old_password)

                        if not (result.get("found") and result.get("verified")):
                            messagebox.showerror(
                                "Error",
                                "Incorrect password",
                                parent=self.interface_root,
                            )
                            password_entry.delete(0, "end")
                            return

                        from check_systems import passwords_confirmation

                        password_state = passwords_confirmation(
                            frame, self.interface_root
                        )
                        if not password_state["confirmed"]:
                            return

                        new_password = password_state["password"]
                        self.dbm.change_admin_password(new_password)

                        messagebox.showinfo(
                            "Success",
                            "Administrator password updated successfully!",
                            parent=self.interface_root,
                        )

                        set_view(self, self.show_console_menu)

                    preset_button(
                        frame,
                        text="next",
                        width=25,
                        command=submit,
                    ).pack(pady=10)

                    preset_button(
                        frame,
                        text="Back",
                        width=25,
                        command=lambda: set_view(self, self.show_console_menu),
                    ).pack(pady=10)

                else:
                    messagebox.showerror(
                        "Error",
                        "Incorrect password. Operation cancelled.",
                        parent=self.interface_root,
                    )
                    set_view(self, self.show_console_menu)

            except Exception as error:
                messagebox.showerror("Error", f": {error}", parent=self.interface_root)
        else:
            messagebox.showinfo(
                "Cancelled", "Password change cancelled.", parent=self.interface_root
            )
            set_view(self, self.show_console_menu)

    def encryption_software_access(self):
        """
        Opens the Encryption Software window by instantiating the
        EncryptionSoftware class from encryption_software_V6.
        """

        from encryption_software import EncryptionSoftware

        EncryptionSoftware()

    def show_database_management(self, frame):
        """
        Renders the database management submenu with options to create or
        delete the database, view table contents, or return to the main menu.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        preset_label(
            frame, text="Database Management", font=self.styles["heading"]
        ).pack(pady=10)

        buttons = [
            ("Create Database", self.create_database),
            ("Delete Database", self.delete_database),
            ("View Database", lambda: set_view(self, self.show_view_database)),
            ("Export Table to CSV", self.table_to_csv),
            ("Back to Main Menu", lambda: set_view(self, self.show_console_menu)),
        ]

        for text, command in buttons:
            preset_button(frame, text=text, width=30, command=command).pack(pady=5)

    def create_database(self):
        """
        Prompts for confirmation and master password verification before
        creating the database. If the database already exists, the operation
        is safe to run as all tables use CREATE TABLE IF NOT EXISTS. Displays
        a success or error message on completion.
        """
        if messagebox.askyesno(
            "Confirm Creation",
            f"Are you sure you want to create '{self.db_path}'?\n Note: Nothing will change if the database is already present.",
        ):
            try:
                password = simpledialog.askstring(
                    "Verification",
                    "Please enter Master Password to continue:",
                    show="*",
                    parent=self.interface_root,
                )

                if password == self.MASTER_PASSWORD:
                    self.dbm.create_database()
                    messagebox.showinfo(
                        "Success",
                        f"'{self.db_path}' created successfully.",
                        parent=self.interface_root,
                    )

                else:
                    messagebox.showerror(
                        "Error",
                        "Incorrect password. Operation cancelled.",
                        parent=self.interface_root,
                    )

            except Exception as error:
                messagebox.showerror(
                    "Error", f"Failed to create '{self.db_path}': {error}"
                )

    def delete_database(self):
        """
        Checks the database exists and then prompts for confirmation and master
        password verification before permanently deleting the database file.
        Displays a success or error message on completion.
        """
        if not self.dbm.check_database_exists():
            messagebox.showwarning("Warning", f"'{self.db_path}' does not exist.")
            return

        if messagebox.askyesno(
            "Confirm Delete", f"Are you sure you want to delete '{self.db_path}'?"
        ):
            try:
                password = simpledialog.askstring(
                    "Verification",
                    "Please enter Master Password to continue:",
                    show="*",
                    parent=self.interface_root,
                )

                if password == self.MASTER_PASSWORD:
                    os.remove(self.db_path)
                    messagebox.showinfo(
                        "Success",
                        f"'{self.db_path}' deleted successfully.",
                        parent=self.interface_root,
                    )

                else:
                    messagebox.showerror(
                        "Error", "Incorrect password. Operation cancelled."
                    )

            except Exception as error:
                messagebox.showerror(
                    "Error", f"Failed to delete '{self.db_path}': {error}"
                )

    def show_view_database(self, frame):
        """
        Renders a dropdown allowing the administrator to select a database
        table to view. On selection and confirmation, queries the table and
        navigates to the display view. Shows a warning if the database does
        not exist or the table is empty.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        if not self.dbm.check_database_exists():
            messagebox.showwarning("Warning", f"'{self.db_path}' does not exist.")
            return

        preset_label(
            frame, text="Select Table to View", font=self.styles["heading"]
        ).pack(pady=10)

        tables = [
            "db_logs",
            "admin_logs",
            "users",
            "user_poker_data",
            "user_poker_actions",
        ]

        dropdown = Combobox(
            frame, values=tables, state="readonly", font=self.styles["text"]
        )
        dropdown.pack(pady=10)

        def view_table():
            """
            Reads the selected table name from the dropdown, queries it via
            the database manager and navigates to the table display view.
            Shows an error if no table is selected or the result is empty.
            """
            selected_table = dropdown.get().strip()
            if not selected_table:
                messagebox.showerror("Error", "Please select a table first.")
                return

            dataframe = self.dbm.view_database(selected_table)

            if dataframe.empty:
                messagebox.showinfo(
                    "Info",
                    f"No data found in '{selected_table}'.",
                    parent=self.interface_root,
                )
                return

            set_view(self, lambda f: self.display_table(f, dataframe, selected_table))

        preset_button(
            frame,
            text="View Table",
            width=25,
            command=view_table,
        ).pack(pady=5)

        preset_button(
            frame,
            text="Back",
            width=25,
            command=lambda: set_view(self, self.show_database_management),
        ).pack(pady=5)

    def display_table(self, frame, dataframe, table):
        """
        Renders the contents of a database table in a scrollable Treeview
        widget with alternating row colours. Column widths are automatically
        sized based on the widest value in each column.

        Args:
            frame (Frame): The parent frame to build the view into.
            dataframe (pd.DataFrame): The table data to display.
            table (str): The name of the table, shown in the heading.
        """
        preset_label(frame, text=f"'{table}' Table", font=self.styles["heading"]).pack(
            pady=10
        )

        # Frame to hold Treeview.
        inner_frame = Frame(frame)
        inner_frame.pack(expand=True, fill="both", padx=10, pady=10)

        tree_scroll_y = Scrollbar(inner_frame, orient="vertical")
        tree_scroll_y.pack(side="right", fill="y")

        tree_scroll_x = Scrollbar(inner_frame, orient="horizontal")
        tree_scroll_x.pack(side="bottom", fill="x")

        tree = Treeview(
            inner_frame,
            columns=list(dataframe.columns),
            show="headings",
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set,
        )
        tree.pack(expand=True, fill="both")

        tree_scroll_y.config(command=tree.yview)
        tree_scroll_x.config(command=tree.xview)

        for column in dataframe.columns:
            tree.heading(column, text=column)
            max_width = (
                max(dataframe[column].astype(str).map(len).max(), len(column)) * 10
            )
            tree.column(column, width=max_width, anchor="w")

        # Insert rows with alternating tags for styling, '_' is used to prevent
        # issues with special characters in the data interfering with tag assignment.
        for count, (_, row) in enumerate(dataframe.iterrows()):
            tag = "evenrow" if count % 2 == 0 else "oddrow"
            tree.insert("", "end", values=list(row), tags=(tag,))
        tree.tag_configure("evenrow", background=CS["table_even"])
        tree.tag_configure("oddrow", background=CS["table_odd"])

        preset_button(
            frame,
            text="Back",
            width=25,
            command=lambda: set_view(self, self.show_view_database),
        ).pack(pady=5)

    def table_to_csv(self):
        """
        Prompts the user to select a database table and a save location,
        then exports the selected table's contents to a CSV text file.
        """
        tables = [
            "db_logs",
            "admin_logs",
            "users",
            "user_poker_data",
            "user_poker_actions",
        ]

        table = simpledialog.askstring(
            "Export Table to CSV",
            "Enter the name of the table to export:\nOptions: " + ", ".join(tables),
            parent=self.interface_root,
        )

        if not table:
            messagebox.showerror("Returning to Menu", "No table name provided.")
            return

        save_path = filedialog.asksaveasfilename(
            title="Save CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )

        if not save_path:
            messagebox.showerror("Returning to Menu", "No save location provided.")
            return

        try:
            self.dbm.export_table_to_csv(table, save_path)
            messagebox.showinfo(
                "Success",
                f"'{table}' exported to:\n{save_path}",
                parent=self.interface_root,
            )
        except Exception as error:
            messagebox.showerror(
                "Error",
                f"Failed to export '{table}': {error}",
                parent=self.interface_root,
            )

    def show_user_management(self, frame):
        """
        Renders the user management submenu with options to fetch, add, edit,
        or delete user records. Shows a warning if the database does not exist.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        if not self.dbm.check_database_exists():
            messagebox.showwarning("Warning", f"'{self.db_path}' does not exist.")
            return

        preset_label(frame, text="User Management", font=self.styles["heading"]).pack(
            pady=10
        )

        buttons = [
            ("Return User Information", lambda: set_view(self, self.fetch_user_record)),
            ("Add User", lambda: set_view(self, self.add_user)),
            ("Edit User", lambda: set_view(self, self.edit_user)),
            ("Delete User", lambda: set_view(self, self.delete_user)),
            ("Back to Main Menu", lambda: set_view(self, self.show_console_menu)),
        ]

        for text, command in buttons:
            preset_button(frame, text=text, width=30, command=command).pack(pady=5)

    def fetch_user_record(self, frame):
        """
        Renders a search form allowing lookup by user ID, username, or both.
        When both are provided, verifies that they refer to the same user
        before proceeding. Navigates to the record display view on a
        successful lookup.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        preset_label(frame, text="Enter User ID", font=self.styles["heading"]).pack(
            pady=10
        )

        user_id_entry = preset_entry(frame)
        user_id_entry.pack(pady=5)

        preset_label(frame, text="Enter Username", font=self.styles["heading"]).pack(
            pady=10
        )
        username_entry = preset_entry(frame)
        username_entry.pack(pady=5)

        def lookup_user():
            """
            Resolves the entered user ID and/or username to a full user record.
            Validates cross-referencing when both are provided and then navigates
            to the record display view. Shows appropriate errors for mismatches,
            non-numeric IDs, or missing users.
            """
            if user_id_entry.get().strip() and username_entry.get().strip():
                user_id = user_id_entry.get().strip()
                username = username_entry.get().strip()
                if user_id.isdigit():
                    check_w_user_id = self.dbm.fetch_username(int(user_id))
                    check_w_username = self.dbm.fetch_user_id(username)
                    if check_w_user_id["username"] != username or check_w_username[
                        "user_id"
                    ] != int(user_id):
                        messagebox.showerror(
                            "Error", "User ID and Username do not match."
                        )
                        return
                    record = self.dbm.fetch_user_full_record(user_id=int(user_id))
                    if not record:
                        messagebox.showinfo("Not Found", "User not found.")
                        return
                else:
                    messagebox.showerror("Error", "User ID must be numeric.")
                    return
                set_view(self, lambda f: self.display_user_record(f, record))

            elif user_id_entry.get().strip():
                user_id = user_id_entry.get().strip()
                if user_id.isdigit():
                    record = self.dbm.fetch_user_full_record(user_id=int(user_id))
                    if not record:
                        messagebox.showinfo("Not Found", "User not found.")
                        return
                else:
                    messagebox.showerror("Error", "User ID must be numeric.")
                    return
                set_view(self, lambda f: self.display_user_record(f, record))

            elif username_entry.get().strip():
                username = username_entry.get().strip()
                record = self.dbm.fetch_user_full_record(username=username)
                if not record:
                    messagebox.showinfo("Not Found", "User not found.")
                    return
                set_view(self, lambda f: self.display_user_record(f, record))

            else:
                messagebox.showerror("Error", "No input provided.")
                return

        preset_button(
            frame,
            text="Search",
            width=25,
            command=lookup_user,
        ).pack(pady=10)

        preset_button(
            frame,
            text="Back",
            width=25,
            command=lambda: set_view(self, self.show_user_management),
        ).pack(pady=5)

    def display_user_record(self, frame, record):
        """
        Renders a read-only view of a user's full record, including username,
        password hash, account type, balance, creation timestamp and
        termination status with details if applicable.

        Args:
            frame (Frame): The parent frame to build the view into.
            record (dict): The user record dictionary as returned by
                           fetch_user_full_record().
        """
        preset_label(
            frame,
            text=f"User Information: {record.get('username')}",
            font=self.styles["heading"],
        ).pack(pady=10)

        for key, value in [
            ("Username", record["username"]),
            ("Password", record["password_hash"]),
            ("Account Type", "Registered" if record["registered"] else "Guest"),
            ("Balance", record["balance"]),
            ("Creation Time", record["created_at"]),
        ]:
            preset_label(frame, text=f"{key}: {value}", anchor="w").pack(
                fill="x", padx=20, pady=2
            )

        preset_button(
            frame,
            text="Back",
            width=25,
            command=lambda: set_view(self, self.show_user_management),
        ).pack(pady=10)

    def add_user(self, frame):
        """
        Renders a username input form for creating a new user. Validates that
        the username is non-empty and not already taken before proceeding to
        account type selection.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        preset_label(frame, text="Enter Username", font=self.styles["heading"]).pack(
            pady=10
        )

        username_entry = preset_entry(frame)
        username_entry.pack(pady=5)

        def next():
            """
            Reads the entered username, validates it is non-empty and unique,
            then navigates to the account type selection view.
            """
            username = username_entry.get().strip()

            if not username:
                messagebox.showinfo("Cancelled", "No username provided.")
                set_view(self, self.show_user_management)
                return

            if self.dbm.fetch_user_presence(username).get("found"):
                messagebox.showerror("Error", "Username already exists.")
                return

            set_view(self, lambda f: self.choose_account_type(f, username))

        preset_button(frame, text="Next", width=25, command=next).pack(pady=10)

        preset_button(
            frame,
            text="Back",
            width=25,
            command=lambda: set_view(self, self.show_user_management),
        ).pack(pady=5)

    def choose_account_type(self, frame, username):
        """
        Presents a choice between creating a registered account (with password)
        or a temporary guest account (without password). Navigates to password
        creation for registered accounts, or creates the guest account
        immediately and returns to user management.

        Args:
            frame (Frame): The parent frame to build the view into.
            username (str): The username for the account being created.
        """
        preset_label(frame, text="Account Type", font=self.styles["heading"]).pack(
            pady=10
        )

        def register():
            """Navigates to the password creation view for a registered account."""
            set_view(self, lambda f: self.create_password(f, username))

        def guest():
            """
            Creates a temporary guest account with no password and navigates
            back to the user management menu.
            """
            self.dbm.register_user(username, None, False)

            messagebox.showinfo(
                "Success", f"Temporary guest account '{username}' created successfully!"
            )

            set_view(self, self.show_user_management)

        preset_button(
            frame,
            text="Register Account",
            width=25,
            command=register,
        ).pack(pady=5)

        preset_button(
            frame,
            text="Temporary Guest Account",
            width=25,
            command=guest,
        ).pack(pady=5)

        preset_button(
            frame,
            text="Back",
            width=25,
            command=lambda: set_view(self, self.show_user_management),
        ).pack(pady=5)

    def create_password(self, frame, username):
        """
        Launches the password confirmation dialog in a loop until a valid
        confirmed password is provided and then creates the registered user
        account and returns to the user management menu.

        Args:
            frame (Frame): The parent frame used to position the dialog.
            username (str): The username for the account being created.
        """

        while True:
            from check_systems import passwords_confirmation

            password_state = passwords_confirmation(frame, self.interface_root)
            if password_state["confirmed"]:
                self.dbm.register_user(username, password_state["password"], True)

                messagebox.showinfo(
                    "Success", f"Account for '{username}' created successfully!"
                )

                set_view(self, self.show_user_management)
                break

    def edit_user(self, frame):
        """
        Renders a search form for locating a user to edit, accepting a user ID,
        username, or both. Cross-validates when both are provided. Navigates to
        the edit form on a successful lookup.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        preset_label(frame, text="Enter User ID:", font=self.styles["heading"]).pack(
            pady=10
        )

        user_id_entry = preset_entry(frame)
        user_id_entry.pack(pady=5)

        preset_label(frame, text="Enter Username:", font=self.styles["heading"]).pack(
            pady=10
        )

        username_entry = preset_entry(frame)
        username_entry.pack(pady=5)

        def next():
            """
            Resolves the entered user ID and/or username to a full user record,
            cross-validating when both are provided and then navigates to the edit
            form. Shows appropriate errors for mismatches, non-numeric IDs, or
            missing users.
            """
            if user_id_entry.get().strip() and username_entry.get().strip():
                user_id = user_id_entry.get().strip()
                username = username_entry.get().strip()
                if user_id.isdigit():
                    check_w_user_id = self.dbm.fetch_username(int(user_id))
                    check_w_username = self.dbm.fetch_user_id(username)
                    if check_w_user_id["username"] != username or check_w_username[
                        "user_id"
                    ] != int(user_id):
                        messagebox.showerror(
                            "Error", "User ID and Username do not match."
                        )
                        return

                    record = self.dbm.fetch_user_full_record(user_id=int(user_id))

                    if not record:
                        messagebox.showinfo("Not Found", "User not found.")
                        return

                else:
                    messagebox.showerror("Error", "User ID must be numeric.")
                    return

                set_view(self, lambda f: self.show_edit_form(f, record))

            elif user_id_entry.get().strip():
                user_id = user_id_entry.get().strip()
                if user_id.isdigit():
                    record = self.dbm.fetch_user_full_record(user_id=int(user_id))

                    if not record:
                        messagebox.showinfo("Not Found", "User not found.")
                        return
                else:
                    messagebox.showerror("Error", "User ID must be numeric.")
                    return

                set_view(self, lambda f: self.show_edit_form(f, record))

            elif username_entry.get().strip():
                username = username_entry.get().strip()
                if not username:
                    messagebox.showerror("Error", "No input provided.")
                    return

                record = self.dbm.fetch_user_full_record(username=username)

                if not record:
                    messagebox.showinfo("Not Found", "User not found.")
                    return

                set_view(self, lambda f: self.show_edit_form(f, record))

            else:
                messagebox.showerror("Error", "No input provided.")
                return

        preset_button(frame, text="Next", width=25, command=next).pack(pady=10)

        preset_button(
            frame,
            text="Back",
            width=25,
            command=lambda: set_view(self, self.show_user_management),
        ).pack(pady=5)

    def show_edit_form(self, frame, record):
        """
        Renders an editable form pre-populated with the current user record.
        Allows changing username, password, account type, balance and
        termination status. Calls change_user_record with only the fields
        that have been filled in.

        Args:
            frame (Frame): The parent frame to build the view into.
            record (dict): The current user record dictionary.
        """
        preset_label(
            frame,
            text=f"Edit User:\n{record['user_id']} | {record['username']}",
            font=self.styles["heading"],
        ).pack(pady=10)

        preset_label(frame, text="New Username:").pack()
        username_entry = preset_entry(frame)
        username_entry.pack()

        preset_label(frame, text="New Password:").pack()
        password_entry = preset_entry(frame, show="*")
        password_entry.pack()

        preset_label(frame, text="New Account Type:").pack()
        type_box = Combobox(frame, values=["Registered", "Temporary"], state="readonly")
        type_box.set("Registered" if not record.get("temporary") else "Temporary")
        type_box.pack()

        preset_label(frame, text="New Balance:").pack()
        balance_entry = preset_entry(frame)
        balance_entry.insert(0, str(record.get("balance", 0)))
        balance_entry.pack()

        def save():
            """
            Collects all non-empty field values from the form, validates the
            balance as a float then calls change_user_record to
            apply the changes.
            """
            kwargs = {"user_id": record["user_id"]}

            if username_entry.get().strip():
                kwargs["new_username"] = username_entry.get().strip()

            if password_entry.get().strip():
                kwargs["new_password"] = password_entry.get().strip()

            kwargs["new_account_type"] = type_box.get() == "Registered"

            try:
                kwargs["new_balance"] = float(balance_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Invalid balance.")
                return

            self.dbm.change_user_record(**kwargs)

            messagebox.showinfo("Success", "User updated successfully.")
            set_view(self, self.show_user_management)

        preset_button(
            frame,
            text="Save Changes",
            width=25,
            command=save,
        ).pack(pady=10)

        preset_button(
            frame,
            text="Back",
            width=25,
            command=lambda: set_view(self, self.show_user_management),
        ).pack(pady=5)

    def delete_user(self, frame):
        """
        Renders a username input form for deleting a user account. Prevents
        deletion of the Administrator account. Prompts for confirmation before
        permanently removing the record.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        preset_label(
            frame, text="Enter Username to Delete", font=self.styles["heading"]
        ).pack(pady=10)

        username_entry = preset_entry(frame)
        username_entry.pack(pady=5)

        def next():
            """
            Validates the entered username exists and is not the Administrator
            account, confirms deletion with the user and then resolves the
            username to a user ID and calls delete_user_record.
            """
            username = username_entry.get().strip()
            if not username or not self.dbm.fetch_user_presence(username).get("found"):
                messagebox.showerror("Error", "Username does not exist.")
                return

            if username == "Administrator":
                messagebox.showerror(
                    "Error", "Cannot delete the Administrator account."
                )
                return

            if messagebox.askyesno("Confirm Delete", f"Delete user '{username}'?"):
                result = self.dbm.fetch_user_id(username)
                if result["found"]:
                    self.dbm.delete_user_record(result["user_id"])

                messagebox.showinfo("Success", f"User '{username}' deleted.")
                set_view(self, self.show_user_management)

        preset_button(frame, text="Delete", width=25, command=next).pack(pady=10)

        preset_button(
            frame,
            text="Back",
            width=25,
            command=lambda: set_view(self, self.show_user_management),
        ).pack(pady=5)


# Minimum rounds played before a user may enable Tournament Mode.
TOURNAMENT_MIN_ROUNDS = 25

# Max bots, difficulties randomly distributed 0-100 and reshuffled each round.
ENDLESS_BOT_COUNT = 9

DEFAULT_SETTINGS = {
    # Harrogate Hold 'Em.
    "bot_count": 3,
    "bot_balance": 1000,
    "small_blind": 50,
    "big_blind": 100,
    "bot_difficulty": 50,
    # Tournament.
    "tournament_mode": False,
    "tournament_rounds": 5,
    "tournament_players": 4,  # Total players including user.
    "win_criteria": "eliminate_all",
    "win_criteria_target": 1000,  # Used when criteria is "earn_target".
    # Endless.
    "endless_mode": False,
    # General.
    "starting_balance": 10000,
}

TOURNAMENT_WIN_CRITERIA = {
    "eliminate_all": "Eliminate all opponents",
    "earn_target": "Earn a target amount of money",
    "survive_rounds": "Survive a set number of rounds",
    "last_man_blind": "Outlast opponents as blinds escalate",
}


class CasinoInterface(BaseInterface):
    """
    Main casino interface for users and administrators. Handles login,
    account management, game selection and mode-specific rules such as
    tournament and endless play.

    Unlike the other interfaces, CasinoInterface accepts constructor
    arguments so __init__ is overridden to capture them before delegating
    to BaseInterface.__init__.
    """

    WINDOW_BG_KEY = "casino"

    def __init__(self, administrator=False, user_data=None):
        """
        Stores constructor arguments as instance state and then calls
        super().__init__() which builds the window, checks the database,
        and starts the mainloop.

        Args:
            administrator (bool): If True, launches in administrator mode,
                                  bypassing login.
            user_data (dict, optional): Pre-populated user session dict with
                                        keys 'user_id', 'username',
                                        'administrator'. Defaults to an
                                        unsigned-in state if None.
        """
        self._administrator = administrator
        self._user_data_init = user_data

        # Personalised game settings for HHE — set before mainloop starts.
        self.settings = dict(DEFAULT_SETTINGS)

        super().__init__()

    # Uses a property to dynamically generate the window title based on administrator
    # status, since this is not known until after the constructor arguments are processed.
    @property
    def WINDOW_TITLE(self):
        """
        Dynamic window title based on administrator mode.
        """
        return (
            "One Less Time Casino — Administrator Access"
            if self._administrator
            else "One Less Time Casino"
        )

    def setup_user_data(self):
        """
        Initialises self.user_data from the constructor arguments.
        """
        if self._user_data_init is not None:
            self.user_data = self._user_data_init
        else:
            self.user_data = {
                "user_id": None,
                "username": None,
                "administrator": False,
            }

        if self._administrator:
            self.user_data["user_id"] = 0
            self.user_data["username"] = "Administrator"
            self.user_data["administrator"] = True

    def startup(self):
        # User data must be ready before any view is rendered.
        self.setup_user_data()
        self.dbm.check_expired_guest_account()
        return self.casino_menu

    # Helpers.

    def user_linked(self):
        """
        Returns True if a user account is currently linked to this session.

        Returns:
            bool: True if a user is linked, False otherwise.
        """
        return bool(self.user_data.get("username"))

    def fetch_rounds_played(self):
        """
        Retrieves the number of poker rounds the current user has played
        from the database. Returns 0 for administrators or if the data
        cannot be fetched.

        Returns:
            int: Rounds played, or 0 on failure / admin session.
        """
        if self.user_data.get("administrator"):
            # Administrators are never blocked by the rounds threshold.
            return TOURNAMENT_MIN_ROUNDS

        user_id = self.user_data.get("user_id")
        if not user_id:
            return 0

        try:
            statistics = self.dbm.fetch_player_statistics(user_id)
            return int(statistics["rounds_played"]) if statistics else 0
        except Exception:
            return 0

    def require_linked(self, action_label="this"):
        """
        Shows a warning dialog if no account is linked.

        Args:
            action_label (str): Short name for what was attempted, used in
                                the message (e.g. "the Game Menu").

        Returns:
            bool: True if the account is linked and the caller may proceed,
                  False if the user should be blocked.
        """
        if self.user_linked():
            return True
        messagebox.showwarning(
            "Account Required",
            f"You must be signed in to access {action_label}.\n\n"
            "Please register or log in first.",
        )
        return False

    def fetch_special_scores(self):
        """
        Retrieves the player's personal best score for Endless mode from
        the database.

        Returns:
            int: The maximum rounds survived in Endless mode, or 0 if no
                 score exists or the user is not signed in.
        """
        user_id = self.user_data.get("user_id")
        if not user_id:
            return 0

        try:
            scores = self.dbm.fetch_special_mode_scores(user_id)
            if not scores:
                return 0
            # Endless is the only special mode currently tracked, so we can return it directly.
            # If more modes are added, this should be refactored to specify which score is requested.
            return scores["endless_high_score"]
        except Exception:
            return 0

    def casino_menu(self, frame):
        """
        Displays the main casino menu. Displays a sign-in prompt if no user
        is logged in, or a personalised welcome message if one is.

        Game Menu and Game Settings buttons are disabled with an explanatory
        note when no account is linked.  All other buttons are always active.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        preset_label(
            frame,
            text="Welcome to\nOne Less Time Casino",
            font=self.styles["heading"],
        ).pack(pady=15)

        linked = self.user_linked()

        if not linked:
            preset_label(
                frame,
                text="Please sign in.\nIf you do not have an account please either register or create a guest account.",
                font=self.styles["emphasis"],
            ).pack(pady=10)
        else:
            preset_label(
                frame,
                text=f"Welcome, {self.user_data['username']}",
                font=self.styles["subheading"],
            ).pack(pady=10)

        preset_button(
            frame,
            text="Game Menu",
            width=30,
            state="normal" if linked else "disabled",
            command=lambda: set_view(self, self.show_game_menu),
        ).pack(pady=5)

        if not linked:
            preset_label(
                frame,
                text="Sign in to access the Game Menu.",
                font=self.styles["emphasis"],
            ).pack()

        if not linked:
            preset_button(
                frame,
                text="Sign Up",
                width=30,
                command=self.user_register,
            ).pack(pady=5)

            preset_button(
                frame,
                text="Login",
                width=30,
                command=self.user_login_setup,
            ).pack(pady=5)

        preset_button(
            frame,
            text="Account Information",
            width=30,
            state="normal" if linked else "disabled",
            command=lambda: set_view(self, self.fetch_user_record),
        ).pack(pady=5)

        if not linked:
            preset_label(
                frame,
                text="Sign in to view account information.",
                font=self.styles["emphasis"],
            ).pack()

        preset_button(
            frame,
            text="Exit Casino",
            width=30,
            command=self.casino_exit,
        ).pack(pady=5)

    def show_game_menu(self, frame):
        """
        Displays the game selection menu. Requires an account to be linked;
        redirects to the main menu with a warning if not.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        if not self.require_linked("the Game Menu"):
            set_view(self, self.casino_menu)
            return

        preset_label(
            frame,
            text="Game Menu",
            font=self.styles["heading"],
        ).pack(pady=20)

        buttons = [
            ("WhiteJoe", self.whitejoe_rules),
            ("Harrogate Hold 'Em", self.harrogate_hold_em_rules),
            ("Leaderboard", lambda: set_view(self, self.show_leaderboard)),
            ("Game Settings", lambda: set_view(self, self.game_settings)),
            ("Return to Main Menu", lambda: set_view(self, self.casino_menu)),
        ]

        for text, command in buttons:
            preset_button(
                frame,
                text=text,
                width=30,
                command=command,
            ).pack(pady=5)

    def user_register(self):
        """
        Initiates the registration flow. If the administrator is already
        signed in, prompts for confirmation before proceeding.
        """
        if self.user_data["administrator"]:
            if not messagebox.askyesno(
                "Administrator",
                "You are already signed in as an administrator.  "
                "Register a new account?",
            ):
                return

        set_view(self, lambda f: self.username_input(f, registered=True))

    def user_login_setup(self):
        """
        Initiates the login flow. If the administrator is signed in, prompts
        for confirmation and clears the administrator flag if they choose to
        sign in as a different user.
        """
        if self.user_data["administrator"]:
            if messagebox.askyesno(
                "Administrator",
                "You are already signed in as an administrator.  "
                "Sign in with another account?",
            ):
                self.user_data["administrator"] = False
            else:
                return
        set_view(self, lambda f: self.username_input(f, registered=False))

    def username_input(self, frame, registered):
        """
        Displays a username input form used for both registration and login.

        Args:
            frame (Frame): The parent frame to build the view into.
            registered (bool): If True, validates uniqueness for registration.
        """
        preset_label(
            frame,
            text="Enter Username",
            font=self.styles["heading"],
        ).pack(pady=10)

        username_entry = Entry(frame, font=self.styles["text"])
        username_entry.pack(pady=5)

        def proceed():
            """Validates the username and routes to the next step."""
            username = username_entry.get().strip()
            if not username:
                messagebox.showinfo("Cancelled", "No username provided.")
                set_view(self, self.casino_menu)
                return

            if username.lower() == "administrator":
                messagebox.showerror(
                    "Error",
                    "The username 'Administrator' is reserved and may not be used.",
                )
                return

            if registered and self.dbm.fetch_user_presence(username).get("found"):
                messagebox.showerror("Error", "Username already exists.")
                return

            set_view(
                self,
                (
                    (lambda f: self.set_account_type(f, username))
                    if registered
                    else (lambda f: self.user_login(f, username))
                ),
            )

        preset_button(
            frame,
            text="Next",
            width=25,
            command=proceed,
        ).pack(pady=10)

        preset_button(
            frame,
            text="Back",
            width=25,
            command=lambda: set_view(self, self.casino_menu),
        ).pack(pady=5)

    def set_account_type(self, frame, username):
        """
        Presents a choice between a registered account (with password) or a
        temporary guest account (without password).

        Args:
            frame (Frame): The parent frame to build the view into.
            username (str): The username for the account being created.
        """
        preset_label(frame, text="Account Type", font=self.styles["heading"]).pack(
            pady=10
        )

        def register():
            set_view(self, lambda f: self.create_password(f, username))

        def temporary():
            self.dbm.register_user(username, None, False)
            result = self.dbm.fetch_user_id(username)
            self.user_data["user_id"] = result["user_id"] if result["found"] else None
            self.user_data["username"] = username
            messagebox.showinfo("Success", f"Temporary account '{username}' created.")
            set_view(self, self.casino_menu)

        for text, command in (
            ("Register Account", register),
            ("Temporary Guest Account", temporary),
            ("Back", lambda: set_view(self, self.casino_menu)),
        ):
            preset_button(
                frame,
                text=text,
                width=25,
                command=command,
            ).pack(pady=5)

    def create_password(self, frame, username):
        """
        Launches the password confirmation dialog, creates the registered user
        account on success and returns to the main casino menu.

        Args:
            frame (Frame): The parent frame used to position the dialog.
            username (str): The username for the account being created.
        """

        from check_systems import passwords_confirmation

        password_info = passwords_confirmation(frame, self.interface_root)
        if password_info["confirmed"]:
            self.dbm.register_user(username, password_info["password"], True)
            result = self.dbm.fetch_user_id(username)
            self.user_data["user_id"] = result["user_id"] if result["found"] else None
            self.user_data["username"] = username
            messagebox.showinfo(
                "Success", f"Account '{username}' created successfully."
            )
        else:
            messagebox.showinfo("Cancelled", "Password not set.  Returning to menu.")
        set_view(self, self.casino_menu)

    def user_login(self, frame, username):
        """
        Displays a password entry form for logging in as the given username.

        Args:
            frame (Frame): The parent frame to build the view into.
            username (str): The username attempting to log in.
        """
        if not self.dbm.fetch_user_presence(username).get("found"):
            messagebox.showerror("Error", f"Username '{username}' does not exist.")
            set_view(self, lambda f: self.username_input(f, registered=False))
            return

        preset_label(
            frame,
            text=f"Login for '{username}'",
            font=self.styles["heading"],
        ).pack(pady=10)

        preset_label(frame, text="Enter Password:", font=self.styles["text"]).pack(
            pady=5
        )

        password_entry = preset_entry(frame, show="*", font=self.styles["text"])
        password_entry.pack(pady=5)

        def submit_password():
            """Verifies the password and navigates accordingly."""
            password = password_entry.get().strip()
            result = self.dbm.verify_user_password(username, password)

            if result.get("found") and result.get("verified"):
                self.dbm.record_user_login(username)
                uid = self.dbm.fetch_user_id(username)
                self.user_data["user_id"] = uid["user_id"] if uid["found"] else None
                self.user_data["username"] = username
                self.user_data["administrator"] = False
                messagebox.showinfo("Success", f"Welcome back, {username}.")

                set_view(self, self.casino_menu)

            elif result.get("found") and not result.get("verified"):
                messagebox.showerror("Error", "Incorrect password.")
                password_entry.delete(0, "end")
                set_view(self, lambda f: self.username_input(f, registered=False))

            else:
                messagebox.showerror("Error", "Username not found or login failed.")
                set_view(self, lambda f: self.username_input(f, registered=False))

        preset_button(
            frame,
            text="Login",
            width=25,
            command=submit_password,
        ).pack(pady=5)

        preset_button(
            frame,
            text="Cancel",
            width=25,
            command=lambda: set_view(self, self.casino_menu),
        ).pack(pady=5)

    def fetch_user_record(self, frame):
        """
        Retrieves and displays the full record for the currently signed-in
        user. Redirects with a warning if no user is linked.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        if not self.require_linked("Account Information"):
            set_view(self, self.casino_menu)
            return

        record = self.dbm.fetch_user_full_record(username=self.user_data["username"])
        if not record:
            messagebox.showinfo("Not Found", "User record not found.")
            return

        set_view(self, lambda f: self.display_user_record(f, record))

    def display_user_record(self, frame, record):
        """
        Displays a read-only view of the current user's account information.

        Args:
            frame (Frame): The parent frame to build the view into.
            record (dict): The user record dictionary.
        """
        preset_label(
            frame,
            text=f"User Information: {record.get('username')}",
            font=self.styles["heading"],
        ).pack(pady=10)

        for label, value in [
            ("Username", record["username"]),
            ("Account Type", "Registered" if record["registered"] else "Guest"),
            ("Balance", record["balance"]),
            ("Created", record["created_at"]),
        ]:
            preset_label(
                frame,
                text=f"{label}: {value}",
                anchor="w",
            ).pack(fill="x", padx=20, pady=2)

        preset_button(
            frame,
            text="Back",
            width=25,
            command=lambda: set_view(self, self.casino_menu),
        ).pack(pady=10)

    def casino_exit(self):
        """
        Prompts for confirmation before exiting the casino. Displays a
        thank-you and responsible gambling message on confirmation.
        """
        if messagebox.askyesno("Exit Casino", "Do you wish to exit the casino?"):
            messagebox.showinfo(
                "Thank You for Visiting",
                "Thank you for visiting One Less Time Casino.  "
                "And remember, when the fun stops, stop.",
            )
            self.interface_root.destroy()
            sys.exit(0)

    def game_settings(self, frame):
        """
        Displays the Harrogate Hold 'Em settings panel.
        Requires an account to be linked; redirects if not.
        """
        if not self.require_linked("Game Settings"):
            set_view(self, self.casino_menu)
            return

        # Create Canvas with Scrollbar for scrollable content
        canvas = Canvas(frame, bg=self.window_bg, highlightthickness=0)
        scrollbar = Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = Frame(canvas, bg=self.window_bg)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack Canvas and Scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        preset_label(
            scrollable_frame, text="Game Settings", font=self.styles["heading"]
        ).pack(pady=(10, 4))

        # Live variables.
        v_bot_count = IntVar(value=self.settings["bot_count"])
        v_bot_balance = StringVar(value=str(self.settings["bot_balance"]))
        v_small_blind = StringVar(value=str(self.settings["small_blind"]))
        v_big_blind = StringVar(value=str(self.settings["big_blind"]))
        v_bot_diff = IntVar(value=self.settings["bot_difficulty"])
        v_tournament = BooleanVar(value=self.settings["tournament_mode"])
        v_total_rounds = IntVar(value=self.settings["tournament_rounds"])
        v_total_players = IntVar(value=self.settings["tournament_players"])
        v_win_criteria = StringVar(value=self.settings["win_criteria"])
        v_win_target = StringVar(value=str(self.settings["win_criteria_target"]))

        def row(label_text, widget_factory):
            """
            Packs a horizontal row consisting of a descriptive label on
            the left and an input widget (produced by widget_factory) on
            the right into the scrollable settings frame.
            """
            row = Frame(scrollable_frame)
            row.pack(fill="x", padx=30, pady=2)
            preset_label(row, text=label_text, width=32, anchor="w").pack(side="left")
            widget_factory(row).pack(side="left", padx=8)

        preset_label(
            scrollable_frame, text="Table Settings", font=self.styles["subheading"]
        ).pack(fill="x", padx=30, pady=10)
        row(
            "Number of bots (1–9):",
            lambda p: Spinbox(
                p,
                from_=1,
                to=9,
                textvariable=v_bot_count,
                width=6,
                font=self.styles["text"],
            ),
        )
        row(
            "Bot starting balance (£):",
            lambda p: preset_entry(p, textvariable=v_bot_balance, width=10),
        )
        row(
            "Small blind (£):",
            lambda p: preset_entry(p, textvariable=v_small_blind, width=10),
        )
        row(
            "Big blind (£):",
            lambda p: preset_entry(p, textvariable=v_big_blind, width=10),
        )

        preset_label(
            scrollable_frame, text="Bot Difficulty  (0 = easy, 100 = hard)", anchor="w"
        ).pack(fill="x", padx=30, pady=10)
        difficulty_label = preset_label(
            scrollable_frame,
            text=f"Current: {v_bot_diff.get()}",
            font=self.styles["emphasis"],
            anchor="w",
        )
        difficulty_label.pack(fill="x", padx=30)
        Scale(
            scrollable_frame,
            from_=0,
            to=100,
            orient=HORIZONTAL,
            variable=v_bot_diff,
            font=self.styles["text"],
            length=400,
            command=lambda v: difficulty_label.config(text=f"Current: {int(float(v))}"),
        ).pack(anchor="w", padx=30, pady=2)

        preset_label(
            scrollable_frame,
            text="Tournament Mode",
            font=self.styles["subheading"],
            anchor="w",
        ).pack(fill="x", padx=30, pady=10)
        preset_label(
            scrollable_frame,
            text=(
                "Play a series of rounds against bots. Win criteria and blind "
                "escalation are configurable. Unlocks after 25 rounds played."
            ),
            font=self.styles["emphasis"],
            anchor="w",
            wraplength=700,
        ).pack(fill="x", padx=30, pady=(0, 6))
        rounds_played = self.fetch_rounds_played()
        rounds_needed = max(0, TOURNAMENT_MIN_ROUNDS - rounds_played)

        if rounds_needed > 0:
            preset_label(
                scrollable_frame,
                text=(
                    f"Locked — play {rounds_needed} more round"
                    f"{'s' if rounds_needed != 1 else ''} to unlock."
                ),
                font=self.styles["emphasis"],
                anchor="w",
            ).pack(fill="x", padx=30, pady=2)
            self.settings["tournament_mode"] = False
            v_tournament.set(False)
        else:
            toggle_row = Frame(scrollable_frame)
            toggle_row.pack(fill="x", padx=30, pady=2)
            preset_label(
                toggle_row,
                text="Enable Tournament Mode:",
                width=32,
                anchor="w",
            ).pack(side="left")
            Checkbutton(toggle_row, variable=v_tournament).pack(side="left")

            preset_label(
                scrollable_frame,
                text=f"Rounds played: {rounds_played}",
                font=self.styles["emphasis"],
                anchor="w",
            ).pack(fill="x", padx=30, pady=(0, 4))

            row(
                "Number of rounds:",
                lambda p: Spinbox(
                    p,
                    from_=1,
                    to=50,
                    textvariable=v_total_rounds,
                    width=6,
                    font=self.styles["text"],
                ),
            )
            row(
                "Total players (inc. you):",
                lambda p: Spinbox(
                    p,
                    from_=2,
                    to=10,
                    textvariable=v_total_players,
                    width=6,
                    font=self.styles["text"],
                ),
            )

            crit_frame = Frame(scrollable_frame)
            crit_frame.pack(fill="x", padx=30, pady=2)
            preset_label(
                crit_frame,
                text="Round win criteria:",
                width=32,
                anchor="w",
            ).pack(side="left")
            crit_box = Combobox(
                crit_frame,
                textvariable=v_win_criteria,
                values=list(TOURNAMENT_WIN_CRITERIA.keys()),
                state="readonly",
                font=self.styles["text"],
                width=20,
            )
            crit_box.pack(side="left", padx=8)

            crit_desc = preset_label(
                scrollable_frame,
                text=TOURNAMENT_WIN_CRITERIA.get(v_win_criteria.get(), ""),
                font=self.styles["emphasis"],
                anchor="w",
            )
            crit_desc.pack(fill="x", padx=30)

            target_frame = Frame(scrollable_frame)
            preset_label(
                target_frame,
                text="Earn target (£):",
                width=32,
                anchor="w",
            ).pack(side="left")
            preset_entry(
                target_frame,
                textvariable=v_win_target,
                width=12,
            ).pack(side="left", padx=8)

            def on_criteria_change(event=None):
                crit_desc.config(
                    text=TOURNAMENT_WIN_CRITERIA.get(v_win_criteria.get(), "")
                )
                (
                    target_frame.pack(fill="x", padx=30, pady=2)
                    if v_win_criteria.get() == "earn_target"
                    else target_frame.pack_forget()
                )

            crit_box.bind("<<ComboboxSelected>>", on_criteria_change)
            if v_win_criteria.get() == "earn_target":
                target_frame.pack(fill="x", padx=30, pady=2)

        preset_label(
            scrollable_frame,
            text="Endless Mode",
            font=self.styles["subheading"],
            anchor="w",
        ).pack(fill="x", padx=30, pady=10)

        preset_label(
            scrollable_frame,
            text=(
                "Survive as long as possible against 9 bots whose difficulties "
                "are reshuffled every round across the full 0–100 range. "
                "There is no win condition — your score is how many rounds you last."
            ),
            font=self.styles["emphasis"],
            anchor="w",
            wraplength=700,
        ).pack(fill="x", padx=30, pady=(0, 6))

        endless_pb = self.fetch_special_scores()
        preset_label(
            scrollable_frame,
            text=(
                f"High score: {endless_pb} round"
                f"{'s' if endless_pb != 1 else ''} survived"
                if endless_pb > 0
                else "No score yet."
            ),
            font=self.styles["emphasis"],
            anchor="w",
        ).pack(fill="x", padx=30)

        preset_button(
            scrollable_frame,
            text="Start Endless",
            width=20,
            command=self.start_endless,
        ).pack(anchor="w", padx=30, pady=4)

        button_frame = Frame(scrollable_frame)
        button_frame.pack(pady=12)

        def save_settings():
            """Validates and saves Standard and Tournament settings."""
            errors = []

            try:
                bot_count = int(v_bot_count.get())
                if not (1 <= bot_count <= 9):
                    raise Exception("Bot count out of range.")
            except Exception:
                errors.append("Bot count must be between 1 and 9.")
                bot_count = self.settings["bot_count"]

            try:
                bot_balance = int(v_bot_balance.get())
                if bot_balance <= 0:
                    raise Exception("Bot balance must be positive.")
            except Exception:
                errors.append("Bot balance must be a positive integer.")
                bot_balance = self.settings["bot_balance"]

            try:
                small_blind = int(v_small_blind.get())
                if small_blind <= 0:
                    raise Exception("Small blind must be positive.")
            except Exception:
                errors.append("Small blind must be a positive integer.")
                small_blind = self.settings["small_blind"]

            try:
                big_blind = int(v_big_blind.get())
                if big_blind <= 0:
                    raise Exception("Big blind must be a positive integer.")
                raw_small = (
                    int(v_small_blind.get())
                    if v_small_blind.get().isdigit()
                    else small_blind
                )
                if big_blind < raw_small:
                    raise Exception("Big blind must be ≥ small blind.")
            except Exception:
                errors.append("Big blind must be ≥ small blind.")
                big_blind = self.settings["big_blind"]

            try:
                difference = max(0, min(100, int(v_bot_diff.get())))
            except Exception:
                difference = self.settings["bot_difficulty"]

            try:
                total_rounds = int(v_total_rounds.get())
                if total_rounds < 1:
                    raise Exception("Tournament rounds must be ≥ 1.")
            except Exception:
                errors.append("Tournament rounds must be ≥ 1.")
                total_rounds = self.settings["tournament_rounds"]

            try:
                total_players = int(v_total_players.get())
                if not (2 <= total_players <= 10):
                    raise Exception("Tournament players out of range.")
            except Exception:
                errors.append("Tournament players must be between 2 and 10.")
                total_players = self.settings["tournament_players"]

            try:
                win_target = int(v_win_target.get())
                if win_target <= 0:
                    raise Exception("Win target must be positive.")
            except Exception:
                errors.append("Win target must be a positive integer.")
                win_target = self.settings["win_criteria_target"]

            tournament_on = (
                False
                if self.fetch_rounds_played() < TOURNAMENT_MIN_ROUNDS
                else bool(v_tournament.get())
            )

            if errors:
                messagebox.showerror("Settings Error", "\n".join(errors))
                return

            self.settings.update(
                {
                    "bot_count": bot_count,
                    "bot_balance": bot_balance,
                    "small_blind": small_blind,
                    "big_blind": big_blind,
                    "bot_difficulty": difference,
                    "tournament_mode": tournament_on,
                    "tournament_rounds": total_rounds,
                    "tournament_players": total_players,
                    "win_criteria": v_win_criteria.get(),
                    "win_criteria_target": win_target,
                }
            )

            messagebox.showinfo(
                "Settings Saved",
                "Settings updated successfully.",
            )

        def reset_defaults():
            """Resets all settings to DEFAULT_SETTINGS after confirmation."""
            if messagebox.askyesno(
                "Reset Settings",
                "Reset all settings to defaults?",
            ):
                self.settings = dict(DEFAULT_SETTINGS)
                set_view(self, self.game_settings)

        for text, command in (
            ("Save Settings", save_settings),
            ("Reset to Defaults", reset_defaults),
            ("Back to Game Menu", lambda: set_view(self, self.show_game_menu)),
        ):
            preset_button(
                button_frame,
                text=text,
                width=20,
                command=command,
            ).pack(side="left", padx=10)

    def show_leaderboard(self, frame):
        """
        Displays a leaderboard showing the top Endless scores
        across all players in the database. Uses get_all_players_data()
        to retrieve the full data set and sorts by each metric.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        preset_label(
            frame,
            text="Leaderboard",
            font=self.styles["heading"],
        ).pack(pady=(15, 5))

        try:
            all_data = self.dbm.fetch_all_players_data()
        except Exception:
            all_data = []

        def board_section(title, key, unit="rounds"):
            """Displays a titled top-5 table."""
            preset_label(
                frame,
                text=title,
                font=self.styles["subheading"],
            ).pack(pady=(12, 2))
            Frame(frame, height=1, bg=CS["separator"]).pack(fill="x", padx=40)

            candidates = [
                p for p in all_data if p.get(key, 0)
            ]  # Filter out players with no score.
            ranked = bubble_sort(candidates, key=key, reverse=True)[:5]

            # Use binary_search_by_id for the username lookup.
            sorted_by_id = bubble_sort(
                all_data, key="user_id", reverse=False
            )  # Ensure data is sorted by user_id for binary search.
            for entry in ranked:
                index = binary_search_by_id(sorted_by_id, entry["user_id"])
                if index != -1:
                    try:
                        result = self.dbm.fetch_username(sorted_by_id[index]["user_id"])
                        username = (
                            result["username"]
                            if result["found"]
                            else f"User {entry['user_id']}"
                        )
                    except Exception:
                        username = f"User {entry['user_id']}"
                else:
                    username = f"User {entry['user_id']}"

            if not ranked:
                preset_label(
                    frame,
                    text="No scores recorded yet.",
                ).pack(pady=4)
                return

            for index, entry in enumerate(ranked, 1):
                try:
                    result = self.dbm.fetch_username(entry["user_id"])
                    username = (
                        result["username"]
                        if result["found"]
                        else f"User {entry['user_id']}"
                    )
                except Exception:
                    username = f"User {entry['user_id']}"

                score = int(entry[key])
                preset_label(
                    frame,
                    text=f"  {index}.  {username:<20}  {score} {unit}",
                    anchor="w",
                ).pack(fill="x", padx=60, pady=1)

        board_section("Endless — Most Rounds Survived", "endless_high_score")

        preset_button(
            frame,
            text="Back to Game Menu",
            width=25,
            command=lambda: set_view(self, self.show_game_menu),
        ).pack(pady=14)

    def show_special_mode_summary(self, rounds_survived):
        """
        Shows a post-game summary dialog for available special modes (currently just Endless),
        comparing the result to the player's stored personal best and
        updating the database if a new record was set.

        Args:
            rounds_survived (int): How many rounds the player survived.
        """
        user_id = self.user_data.get("user_id")
        endless_pb = self.fetch_special_scores()

        old_pb = endless_pb
        pb_key = "endless_high_score"
        label = "Endless"

        new_record = rounds_survived > old_pb

        if new_record and user_id:
            try:
                self.dbm.update_special_mode_score(user_id, pb_key, rounds_survived)
            except Exception:
                pass

        if new_record:
            title = "New Personal Best!"
            message = (
                f"{label} Mode — Game Over\n\n"
                f"Rounds survived: {rounds_survived}\n"
                f"Previous best: {old_pb}\n\n"
                f"New personal best! Well played."
            )
        else:
            title = f"{label} Mode — Game Over"
            message = (
                f"{label} Mode — Game Over\n\n"
                f"Rounds survived: {rounds_survived}\n"
                f"Personal best: {old_pb}\n\n"
            )

        messagebox.showinfo(title, message)
        set_view(self, self.show_game_menu)

    def whitejoe_rules(self):
        """
        Launches the WhiteJoe rules window. Requires a linked account.
        On the user agreeing to the rules, starts the WhiteJoe game.
        """
        if not self.require_linked("WhiteJoe"):
            return

        ShowGameRules(self.interface_root).show_whitejoe_rules(
            lambda: self.start_whitejoe()
        )

    def start_whitejoe(self):
        """
        Instantiates and launches the WhiteJoe game, passing the current
        user data.
        """

        from whitejoe import WhiteJoe

        WhiteJoe(self.user_data)

        self.interface_root.destroy()

    def harrogate_hold_em_rules(self):
        """
        Launches the Harrogate Hold 'Em rules window. Requires a linked
        account. On the user agreeing to the rules, starts the game.
        """
        if not self.require_linked("Harrogate Hold 'Em"):
            return

        ShowGameRules(self.interface_root).show_harrogate_hold_em_rules(
            lambda: self.start_hhe()
        )

    def start_hhe(self):
        """
        Builds a bot list from self.settings and launches standard
        Harrogate Hold 'Em.

        If tournament_mode is True but the player is below the round
        threshold, tournament_mode is silently forced off as a safety net
        (the settings panel already prevents this scenario).
        """

        settings = dict(self.settings)
        settings["endless_mode"] = False
        if (
            settings.get("tournament_mode")
            and self.fetch_rounds_played() < TOURNAMENT_MIN_ROUNDS
        ):
            settings["tournament_mode"] = False

        bot_count = settings["bot_count"]
        difficulty = settings["bot_difficulty"]

        from harrogate_hold_em import DEFAULT_BOT_LIST, HarrogateHoldEm

        bot_list = list(DEFAULT_BOT_LIST)
        random.shuffle(bot_list)
        bots = [
            [bot_list[index % len(bot_list)], difficulty] for index in range(bot_count)
        ]

        HarrogateHoldEm(self.user_data, settings, bots)

        self.interface_root.destroy()

    def start_endless(self):
        """
        Launches Endless Mode.

        Nine bots are created with randomly distributed difficulties across
        the full 0–100 range. The settings dict carries 'endless_mode=True'
        so the engine can reshuffle bot difficulties each round and never
        declare a winner. Rounds survived are read back from
        'settings["rounds_survived"]' after the game returns.
        """

        settings = dict(self.settings)
        settings["endless_mode"] = True
        settings["tournament_mode"] = False
        settings["bot_count"] = ENDLESS_BOT_COUNT
        settings["rounds_survived"] = 0

        from harrogate_hold_em import DEFAULT_BOT_LIST, HarrogateHoldEm

        bot_list = list(DEFAULT_BOT_LIST)
        random.shuffle(bot_list)

        # Spread difficulties evenly across the range then shuffle.
        step = 100 // ENDLESS_BOT_COUNT
        difficulties = [min(100, index * step) for index in range(ENDLESS_BOT_COUNT)]
        random.shuffle(difficulties)

        bots = [
            [bot_list[index % len(bot_list)], difficulties[index]]
            for index in range(ENDLESS_BOT_COUNT)
        ]

        HarrogateHoldEm(self.user_data, settings, bots)

        rounds = int(settings.get("rounds_survived", 0))
        self.show_special_mode_summary(rounds)

        self.interface_root.destroy()


# GAME RULES DISPLAY


class ShowGameRules:

    WJ_RULES = """
        The aim of the game is to beat the dealer by getting higher than the dealer’s hand value.\n
        To beat the dealer you must either:\n
        \t1. Draw a hand value that is higher than the dealer’s hand value.\n
        \t2. The dealer draws a hand value that goes over 21.\n
        \t3. Draw a hand value of 21 on your first two cards, when the dealer does not.\n
        To lose the game:\n
        \t1. Your hand value exceeds 21.\n
        \t2. The dealers hand has a greater value than yours at the end of the round.\n
        You will start off with a whopping £1,000 and the buy in is already paid for.\n
        You will then be offered to place a bet with the amount of money you have, The screen will show how much you have in your possession.\n
        The dealer will then deal out your cards with 2 cards facing upwards for you and 1 card facing up and another hidden for dealer.\n\n
        To play your hand, first you add the card values together and get a hand total anywhere from 4 to 21.\n
        If you’re dealt a ten-value card and an Ace as your first two cards that means you got a Blackjack.\n
        Those get paid 3 to 2 (or 1.5 times your wager) immediately, without playing through the round, as long as the dealer doesn’t also have a Blackjack.\n
        If the dealer also has a Blackjack, you wouldn’t win anything but you also wouldn’t lose your original wager.\n
        You have 5 action to do in total which will decide how you play (The number is the prompt you have to enter in order for the action to take place):\n
        \t1. Hit ~ If you would like more cards to improve your hand total, the dealer will deal you more cards, one at a time, until you either “bust” (go over 21) or you choose to stand.\n
        \tThere is no limit on the number of cards you can take (other than going over a total of 21 obviously).\n
        \t2. Stand ~ If your first two cards are acceptable, you can stand and the dealer will move on to the next player.(Multiplayer not available yet).\n
        \t3. Double Down ~ If you have a hand total that is advantageous to you but you need to take an additional card you can double your initial wager and the dealer will deal you only 1 additional card.\n
        \t4. Surrender ~ If you don’t like your initial hand, you have the option of giving it up in exchange for half your original bet back.\n
        The dealer can only draw up to 16 and stand.
        Once again you are reminded to read the T&C's before playing.
        """

    HHE_RULES = """
        The aim of the game is to use your hole cards in combination with the community cards to make the best possible five-card poker hand.
        \t*Each player is dealt two cards face down (the 'hole cards')
        \t*Over several betting rounds, five more cards are (eventually) dealt face up in the middle of the table.
        \t*These face-up cards are called the 'community cards'. Each player is free to use the community cards in combination with their hole cards to build a five-card poker hand.
        The community cards are revealed in 3 stages, 3 community cards are revealed in the 1st stage and 1 community card in the others:
        \t*1st stage is called the 'Flop'.
        \t*2nd stage is called the 'Turn'.
        \t*3rd stage is called the 'River'.
        Your goal is to construct your five-card poker hands using the best available five cards out of the seven total cards (your two hole cards and the five community cards).
        You can do that by using both your hole cards in combination with three community cards, one hole card in combination with four community cards, or no hole cards.
        If the cards on the table lead to a better combination, you can also play all five community cards and forget about yours.
        In a game of Texas hold'em you can do whatever works to make the best five-card hand.
        If the betting causes all but one player to fold, the lone remaining player wins the pot without having to show any cards.
        For that reason, players don't always have to hold the best hand to win the pot. It's always possible a player can 'bluff' and get others to fold better hands.
        The following are key aspects:
        Given that this is a virtual experience there is no physical button yet it's principles will remain the same.
        At the beginning of the game, one player will be chosen to have the marker.
        The marker determines which player at the table is the acting dealer, after the round the marker will rotate to the next player, a list will be published at the beginning of the game to state the order of the marker.
        The first two players immediately below the marker are the 'small blind' and a 'big blind' respectively.
        The player below of the dealer marker in the small blind receives the first card and then the dealer pitches cards around the table in a clockwise motion from player to player until each has received two starting cards
        The blinds are forced bets that begin the wagering, the blinds ensure there will be some level of 'action' on every hand
        In tournaments, the blinds are raised at regular intervals. You will be given the choice to join a simple 'cash game' or high stakes tournament consisting of multiple tables, each of increasing difficulty.
        The small blind is generally half the amount of the big blind, although this stipulation varies from table to table and can also be dependent on the game being played.
        The moments:
        *Preflop:
        \tThe first round of betting takes place right after each player has been dealt two hole cards. The first player to act is the player below the big blind. The first player has three options:
        \t*Call: match the amount of the big blind
        \t*Raise: increase the bet within the specific limits of the game
        \t*Fold: throw the hand away. If the player chooses to fold, they are out of the game and no longer eligible to win the current hand
        \tThe amount a player can raise to depends on the game that is being played. This setting can be changed depending on what you choose to play.
        \tAfter the first player acts, the play proceeds down the list with each player also having the same three options — to call, to raise, or fold.
        \tOnce the last bet is called and the action is 'closed', the preflop round is over and play moves on to the flop.
        *The Flop:
        \tAfter the first preflop betting round has been completed, the first three community cards are dealt and a second betting round follows involving only the players who have not folded already.
        \tIn this betting round (and subsequent ones), the action starts with the first active player to the left of the button.
        \tAlong with the options to bet, call, fold, or raise, a player now has the option to 'check' if no betting action has occurred beforehand. A check simply means to pass the action to the next player in the hand.
        \tAgain betting continues until the last bet or raise has been called (which closes the action). It also can happen that every player simply chooses not to bet and checks around the 'table', which also ends the betting round.
        *The Turn:
        \tThe fourth community card, called the turn, is dealt face-up following all betting action on the flop.
        \tOnce this has been completed, another round of betting occurs, similar to that on the previous round of play. Again players have the option to check, bet, call, fold, or raise.
        *The River:
        \tThe fifth community card, called the river, is dealt face-up following all betting action on the turn.
        \tOnce this has been completed, another round of betting occurs, similar to what took play on the previous round of play. Once more the remaining players have the option to options to check, bet, call, fold, or raise.
        \tAfter all betting action has been completed, the remaining players in the hand with hole cards now expose their holdings to determine a winner. This is called the showdown.
        *The Showdown:
        \tThe remaining players show their hole cards and with the assistance of the dealer, a winning hand is determined.
        \tThe player with the best combination of five cards wins the pot according to the official poker hand rankings.
        \tA link to the official poker hand rankings will be attached to this document and in the game before you start. 
        \thttps://en.wikipedia.org/wiki/List_of_poker_hands
        Unique to this game is the opportunity to change difficulty (difficulty is regarding the opponents) and create custom characters however their actions are independent to single rounds and any money they lose or earn is not carried forward.
        Once again you are reminded to read the T&C's before playing.
        """

    def __init__(self, root):
        """
        Initialises the ShowGameRules instance with the root window
        reference for font settings and Toplevel parenting.

        Args:
            root: The root Tk window used to bind fonts and parent the
                  rules Toplevel.
        """
        self.interface_root = root
        from gui_helpers import fetch_text_styles

        self.styles = fetch_text_styles(root)

    def show_whitejoe_rules(self, callback):
        """
        Opens the rules window for WhiteJoe and calls the provided callback
        once the user confirms they have read and understood the rules.

        Args:
            callback (callable): A zero-argument function called when the
                                  user clicks Continue.
        """
        self.show_rules_window("WhiteJoe Rules", self.WJ_RULES, callback)

    def show_harrogate_hold_em_rules(self, callback):
        """
        Opens the rules window for Harrogate Hold 'em and calls the provided
        callback once the user confirms they have read and understood the
        rules.

        Args:
            callback (callable): A zero-argument function called when the
                                  user clicks Continue.
        """
        self.show_rules_window("Harrogate Hold 'em Rules", self.HHE_RULES, callback)

    def show_rules_window(self, title, rules_text, callback):
        """
        Creates and displays a modal rules window with a scrollable read-only
        text area and a Continue button.
        The window cannot be closed via the window manager's close button.
        Calls the callback and destroys the window when the user clicks Continue.

        Args:
            title (str): The window title and heading label text.
            rules_text (str): The full rules text to display.
            callback (callable): A zero-argument function called when the
                                  user clicks Continue.
        """
        bg = CS["rules"]
        window = Toplevel(self.interface_root)
        create_window(window, title, bg)

        heading = preset_label(window, text=title, font=self.styles["title"])
        heading.pack(pady=10)

        text_area = scrolledtext.ScrolledText(
            window, wrap=WORD, font=self.styles["terms_and_conditions"]
        )
        text_area.pack(expand=True, fill=BOTH, padx=10)
        text_area.insert(END, rules_text)
        text_area.configure(state="disabled")
        text_area.yview_moveto(0)

        bottom_frame = Frame(window)
        bottom_frame.pack(side=BOTTOM, fill=X, pady=10)

        continue_button = preset_button(
            bottom_frame,
            text="Continue",
            command=lambda: (window.destroy(), callback()),
        )
        continue_button.pack(pady=10)


if __name__ == "__main__":
    AdminInterface() if "--admin" in sys.argv else CasinoInterface(False)
