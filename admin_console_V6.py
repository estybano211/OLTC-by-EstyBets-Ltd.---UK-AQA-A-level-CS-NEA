import os
from tkinter import (
    Tk,
    Frame,
    Label,
    Button,
    Entry,
    messagebox,
    simpledialog,
    ttk,
    Scrollbar,
)
from gui_helpers_V6 import set_view, fetch_font_settings


class Admin_Console:
    """
    Provides the administrator console interface, giving access to password
    management, the encryption software, database management, and user
    management. Sensitive operations are protected by a master password.
    """

    def __init__(self):
        """
        Initialises the Admin Console window, loads the database manager and
        font styles, and starts at the main console menu.
        """
        self.adm_console_root = Tk()
        self.adm_console_root.title("One More Time Casino - Administrator Console")

        try:
            self.adm_console_root.attributes("-fullscreen", True)
        except Exception:
            pass

        from database_management_and_logging_V6 import DatabaseManagement, DB_FILE

        self.dbm = DatabaseManagement()
        self.DB_FILE = DB_FILE

        self.MASTER_PASSWORD = "Master_Password"

        self.styles = fetch_font_settings(self.adm_console_root)

        self.main_frame = Frame(self.adm_console_root)
        self.main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        self.current_section_frame = None

        set_view(self, self.show_console_menu)

        self.adm_console_root.mainloop()

    def show_console_menu(self, frame):
        """
        Renders the main admin console menu with navigation buttons for all
        available administrative operations.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        Label(
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
            ("Exit", self.adm_console_root.destroy),
        ]

        for text, command in buttons:
            Button(
                frame, text=text, font=self.styles["button"], width=30, command=command
            ).pack(pady=5)

    def change_admin_password(self, frame):
        """
        Renders the admin password change flow. Requires master password
        verification before prompting for the current admin password, then
        uses passwords_confirmation to set a new one. Displays appropriate
        error or success dialogs at each stage and returns to the main menu
        on completion or cancellation.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        if not self.dbm.check_database_exists():
            messagebox.showwarning("Warning", f"'{self.DB_FILE}' does not exist.")
            return
        if messagebox.askyesno(
            "Confirm password change",
            f"Are you sure you want to change the administrative password to the system?",
        ):
            try:
                password = simpledialog.askstring(
                    "Verification",
                    "Please enter Master Password to continue:",
                    show="*",
                    parent=self.adm_console_root,
                )

                if password == self.MASTER_PASSWORD:
                    Label(
                        frame,
                        text="Enter Old Administrator Password:",
                        font=self.styles["heading"],
                    ).pack(pady=20)

                    password_entry = Entry(frame, show="*", font=self.styles["text"])
                    password_entry.pack(pady=5)

                    def submit():
                        """
                        Verifies the current admin password, then launches the
                        password confirmation dialog to capture and store the
                        new password. Returns to the main menu on success.
                        """
                        old_password = password_entry.get()
                        result = self.dbm.admin_password_check(old_password)

                        if not (result.get("found") and result.get("verified")):
                            messagebox.showerror("Error", "Incorrect password")
                            password_entry.delete(0, "end")
                            return

                        from check_systems_V6 import passwords_confirmation

                        password_state = passwords_confirmation(
                            frame, self.adm_console_root
                        )
                        if not password_state["confirmed"]:
                            return

                        new_password = password_state["password"]
                        self.dbm.change_admin_password(new_password)

                        messagebox.showinfo(
                            "Success", "Administrator password updated successfully!"
                        )

                        set_view(self, self.show_console_menu)

                    Button(
                        frame,
                        text="next",
                        font=self.styles["button"],
                        width=25,
                        command=submit,
                    ).pack(pady=10)

                    Button(
                        frame,
                        text="Back",
                        font=self.styles["button"],
                        width=25,
                        command=lambda: set_view(self, self.show_console_menu),
                    ).pack(pady=10)

                else:
                    messagebox.showerror(
                        "Error", "Incorrect password. Operation cancelled."
                    )
                    set_view(self, self.show_console_menu)

            except Exception as error:
                messagebox.showerror("Error", f": {error}")
        else:
            messagebox.showinfo("Cancelled", "Password change cancelled.")
            set_view(self, self.show_console_menu)

    def encryption_software_access(self):
        """
        Opens the Encryption Software window by instantiating the
        Encryption_Software class from encryption_software_V6.
        """
        from encryption_software_V6 import Encryption_Software

        Encryption_Software()

    def show_database_management(self, frame):
        """
        Renders the database management submenu with options to create or
        delete the database, view table contents, or return to the main menu.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        Label(frame, text="Database Management", font=self.styles["heading"]).pack(
            pady=10
        )

        buttons = [
            ("Create Database", self.create_database),
            ("Delete Database", self.delete_database),
            ("View Database", lambda: set_view(self, self.show_view_database)),
            ("Back to Main Menu", lambda: set_view(self, self.show_console_menu)),
        ]

        for text, command in buttons:
            Button(
                frame, text=text, font=self.styles["button"], width=30, command=command
            ).pack(pady=5)

    def create_database(self):
        """
        Prompts for confirmation and master password verification before
        creating the database. If the database already exists, the operation
        is safe to run as all tables use CREATE TABLE IF NOT EXISTS. Displays
        a success or error message on completion.
        """
        if messagebox.askyesno(
            "Confirm Creation",
            f"Are you sure you want to create '{self.DB_FILE}'?\n Note: Nothing will change if the database is already present.",
        ):
            try:
                password = simpledialog.askstring(
                    "Verification",
                    "Please enter Master Password to continue:",
                    show="*",
                    parent=self.adm_console_root,
                )

                if password == self.MASTER_PASSWORD:
                    self.dbm.create_database()
                    messagebox.showinfo(
                        "Success", f"'{self.DB_FILE}' created successfully."
                    )

                else:
                    messagebox.showerror(
                        "Error", "Incorrect password. Operation cancelled."
                    )

            except Exception as error:
                messagebox.showerror(
                    "Error", f"Failed to create '{self.DB_FILE}': {error}"
                )

    def delete_database(self):
        """
        Checks the database exists, then prompts for confirmation and master
        password verification before permanently deleting the database file.
        Displays a success or error message on completion.
        """
        if not self.dbm.check_database_exists():
            messagebox.showwarning("Warning", f"'{self.DB_FILE}' does not exist.")
            return

        if messagebox.askyesno(
            "Confirm Delete", f"Are you sure you want to delete '{self.DB_FILE}'?"
        ):
            try:
                password = simpledialog.askstring(
                    "Verification",
                    "Please enter Master Password to continue:",
                    show="*",
                    parent=self.adm_console_root,
                )

                if password == self.MASTER_PASSWORD:
                    os.remove(self.DB_FILE)
                    messagebox.showinfo(
                        "Success", f"'{self.DB_FILE}' deleted successfully."
                    )

                else:
                    messagebox.showerror(
                        "Error", "Incorrect password. Operation cancelled."
                    )

            except Exception as error:
                messagebox.showerror(
                    "Error", f"Failed to delete '{self.DB_FILE}': {error}"
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
            messagebox.showwarning("Warning", f"'{self.DB_FILE}' does not exist.")
            return

        Label(frame, text="Select Table to View", font=self.styles["heading"]).pack(
            pady=10
        )

        tables = [
            "db_logs",
            "admin_logs",
            "users",
            "user_poker_data",
            "user_poker_actions",
        ]

        dropdown = ttk.Combobox(
            frame, values=tables, state="readonly", font=self.styles["text"]
        )
        dropdown.pack(pady=10)

        def view_table():
            """
            Reads the selected table name from the dropdown, queries it via
            the database manager, and navigates to the table display view.
            Shows an error if no table is selected or the result is empty.
            """
            selected_table = dropdown.get().strip()
            if not selected_table:
                messagebox.showerror("Error", "Please select a table first.")
                return

            dataframe = self.dbm.view_database(selected_table)

            if dataframe.empty:
                messagebox.showinfo("Info", f"No data found in '{selected_table}'.")
                return

            set_view(self, lambda f: self.display_table(f, dataframe, selected_table))

        Button(
            frame,
            text="View Table",
            font=self.styles["button"],
            width=25,
            command=view_table,
        ).pack(pady=5)

        Button(
            frame,
            text="Back",
            font=self.styles["button"],
            width=25,
            command=lambda: set_view(self, self.show_database_management),
        ).pack(pady=5)

    def display_table(self, frame, dataframe, table_name):
        """
        Renders the contents of a database table in a scrollable Treeview
        widget with alternating row colours. Column widths are automatically
        sized based on the widest value in each column.

        Args:
            frame (Frame): The parent frame to build the view into.
            dataframe (pd.DataFrame): The table data to display.
            table_name (str): The name of the table, shown in the heading.
        """
        Label(frame, text=f"'{table_name}' Table", font=self.styles["heading"]).pack(
            pady=10
        )

        # Frame to hold Treeview.
        inner_frame = Frame(frame)
        inner_frame.pack(expand=True, fill="both", padx=10, pady=10)

        tree_scroll_y = Scrollbar(inner_frame, orient="vertical")
        tree_scroll_y.pack(side="right", fill="y")

        tree_scroll_x = Scrollbar(inner_frame, orient="horizontal")
        tree_scroll_x.pack(side="bottom", fill="x")

        tree = ttk.Treeview(
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

        for i, (_, row) in enumerate(dataframe.iterrows()):
            tag = "evenrow" if i % 2 == 0 else "oddrow"
            tree.insert("", "end", values=list(row), tags=(tag,))
        tree.tag_configure("evenrow", background="#a50b5e")
        tree.tag_configure("oddrow", background="#feb29c")

        Button(
            frame,
            text="Back",
            font=self.styles["button"],
            width=25,
            command=lambda: set_view(self, self.show_view_database),
        ).pack(pady=5)

    def show_user_management(self, frame):
        """
        Renders the user management submenu with options to fetch, add, edit,
        or delete user records. Shows a warning if the database does not exist.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        if not self.dbm.check_database_exists():
            messagebox.showwarning("Warning", f"'{self.DB_FILE}' does not exist.")
            return

        Label(frame, text="User Management", font=self.styles["heading"]).pack(pady=10)

        buttons = [
            ("Return User Information", lambda: set_view(self, self.fetch_user_record)),
            ("Add User", lambda: set_view(self, self.add_user)),
            ("Edit User", lambda: set_view(self, self.edit_user)),
            ("Delete User", lambda: set_view(self, self.delete_user)),
            ("Back to Main Menu", lambda: set_view(self, self.show_console_menu)),
        ]

        for text, command in buttons:
            Button(
                frame, text=text, font=self.styles["button"], width=30, command=command
            ).pack(pady=5)

    def fetch_user_record(self, frame):
        """
        Renders a search form allowing lookup by user ID, username, or both.
        When both are provided, verifies that they refer to the same user
        before proceeding. Navigates to the record display view on a
        successful lookup.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        Label(frame, text="Enter User ID", font=self.styles["heading"]).pack(pady=10)
        user_id_entry = Entry(frame)
        user_id_entry.pack(pady=5)

        Label(frame, text="Enter Username", font=self.styles["heading"]).pack(pady=10)
        username_entry = Entry(frame)
        username_entry.pack(pady=5)

        def lookup_user():
            """
            Resolves the entered user ID and/or username to a full user record.
            Validates cross-referencing when both are provided, then navigates
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

        Button(
            frame,
            text="Search",
            font=self.styles["button"],
            width=25,
            command=lookup_user,
        ).pack(pady=10)

        Button(
            frame,
            text="Back",
            font=self.styles["button"],
            width=25,
            command=lambda: set_view(self, self.show_user_management),
        ).pack(pady=5)

    def display_user_record(self, frame, record):
        """
        Renders a read-only view of a user's full record, including username,
        password hash, account type, balance, creation timestamp, and
        termination status with details if applicable.

        Args:
            frame (Frame): The parent frame to build the view into.
            record (dict): The user record dictionary as returned by
                           fetch_user_full_record().
        """
        Label(
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
            (
                "Account Status",
                (
                    f"Terminated\n At {record['terminated_at']}\n"
                    f"Because \"{record['termination_reason']}\""
                    if record["terminated"]
                    else "Active"
                ),
            ),
        ]:
            Label(
                frame, text=f"{key}: {value}", font=self.styles["text"], anchor="w"
            ).pack(fill="x", padx=20, pady=2)

        Button(
            frame,
            text="Back",
            font=self.styles["button"],
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
        Label(frame, text="Enter Username", font=self.styles["heading"]).pack(pady=10)

        username_entry = Entry(frame)
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

        Button(
            frame, text="Next", font=self.styles["button"], width=25, command=next
        ).pack(pady=10)

        Button(
            frame,
            text="Back",
            font=self.styles["button"],
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
        Label(frame, text="Account Type", font=self.styles["heading"]).pack(pady=10)

        def register():
            """Navigates to the password creation view for a registered account."""
            set_view(self, lambda f: self.create_password(f, username))

        def guest():
            """
            Creates a temporary guest account with no password and navigates
            back to the user management menu.
            """
            self.dbm.sign_in_user(username, None, False)

            messagebox.showinfo(
                "Success", f"Temporary guest account '{username}' created successfully!"
            )

            set_view(self, self.show_user_management)

        Button(
            frame,
            text="Register Account",
            font=self.styles["button"],
            width=25,
            command=register,
        ).pack(pady=5)

        Button(
            frame,
            text="Temporary Guest Account",
            font=self.styles["button"],
            width=25,
            command=guest,
        ).pack(pady=5)

        Button(
            frame,
            text="Back",
            font=self.styles["button"],
            width=25,
            command=lambda: set_view(self, self.show_user_management),
        ).pack(pady=5)

    def create_password(self, frame, username):
        """
        Launches the password confirmation dialog in a loop until a valid
        confirmed password is provided, then creates the registered user
        account and returns to the user management menu.

        Args:
            frame (Frame): The parent frame used to position the dialog.
            username (str): The username for the account being created.
        """
        from check_systems_V6 import passwords_confirmation

        while True:
            password_state = passwords_confirmation(frame, self.adm_console_root)
            if password_state["confirmed"]:
                self.dbm.sign_in_user(username, password_state["password"], True)

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
        Label(frame, text="Enter User ID:", font=self.styles["heading"]).pack(pady=10)

        user_id_entry = Entry(frame)
        user_id_entry.pack(pady=5)

        Label(frame, text="Enter Username:", font=self.styles["heading"]).pack(pady=10)

        username_entry = Entry(frame)
        username_entry.pack(pady=5)

        def next():
            """
            Resolves the entered user ID and/or username to a full user record,
            cross-validating when both are provided, then navigates to the edit
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

        Button(
            frame, text="Next", font=self.styles["button"], width=25, command=next
        ).pack(pady=10)

        Button(
            frame,
            text="Back",
            font=self.styles["button"],
            width=25,
            command=lambda: set_view(self, self.show_user_management),
        ).pack(pady=5)

    def show_edit_form(self, frame, record):
        """
        Renders an editable form pre-populated with the current user record.
        Allows changing username, password, account type, balance, and
        termination status. A termination reason is required when setting the
        status to Terminated. Calls change_user_record with only the fields
        that have been filled in.

        Args:
            frame (Frame): The parent frame to build the view into.
            record (dict): The current user record dictionary.
        """
        Label(
            frame,
            text=f"Edit User:\n{record['user_id']} | {record['username']}",
            font=self.styles["heading"],
        ).pack(pady=10)

        Label(frame, text="New Username:").pack()
        username_entry = Entry(frame)
        username_entry.pack()

        Label(frame, text="New Password:").pack()
        password_entry = Entry(frame, show="*")
        password_entry.pack()

        Label(frame, text="New Account Type:").pack()
        type_box = ttk.Combobox(
            frame, values=["Registered", "Temporary"], state="readonly"
        )
        type_box.set("Registered" if not record.get("temporary") else "Temporary")
        type_box.pack()

        Label(frame, text="New Balance:").pack()
        balance_entry = Entry(frame)
        balance_entry.insert(0, str(record.get("balance", 0)))
        balance_entry.pack()

        Label(frame, text="Account Status:").pack()
        status_box = ttk.Combobox(
            frame, values=["Active", "Terminated"], state="readonly"
        )
        status_box.set("Active" if not record.get("terminated") else "Terminated")
        status_box.pack()

        Label(
            frame,
            text="New Status Reason (if terminated):",
        ).pack()
        status_reason_entry = Entry(frame)
        status_reason_entry.pack()

        def save():
            """
            Collects all non-empty field values from the form, validates the
            balance as a float and requires a termination reason when the
            status is set to Terminated, then calls change_user_record to
            apply the changes.
            """
            kwargs = {"user_id": record["user_id"]}

            if username_entry.get().strip():
                kwargs["new_username"] = username_entry.get().strip()

            if password_entry.get().strip():
                kwargs["new_password"] = password_entry.get().strip()

            if type_box.get() == "Registered":
                kwargs["new_account_type"] = True
            else:
                kwargs["new_account_type"] = False

            try:
                kwargs["new_balance"] = float(balance_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Invalid balance.")
                return

            if status_box.get() == "Active":
                kwargs["terminated"] = False
                kwargs["reason"] = None
            else:
                kwargs["terminated"] = True
                if status_reason_entry.get().strip():
                    kwargs["reason"] = status_reason_entry.get().strip()
                else:
                    messagebox.showerror(
                        "Error", "Status reason required for terminated accounts."
                    )
                    return

            self.dbm.change_user_record(**kwargs)

            messagebox.showinfo("Success", "User updated successfully.")
            set_view(self, self.show_user_management)

        Button(
            frame,
            text="Save Changes",
            font=self.styles["button"],
            width=25,
            command=save,
        ).pack(pady=10)

        Button(
            frame,
            text="Back",
            font=self.styles["button"],
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
        Label(frame, text="Enter Username to Delete", font=self.styles["heading"]).pack(
            pady=10
        )

        username_entry = Entry(frame)
        username_entry.pack(pady=5)

        def next():
            """
            Validates the entered username exists and is not the Administrator
            account, confirms deletion with the user, then resolves the
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

        Button(
            frame, text="Delete", font=self.styles["button"], width=25, command=next
        ).pack(pady=10)

        Button(
            frame,
            text="Back",
            font=self.styles["button"],
            width=25,
            command=lambda: set_view(self, self.show_user_management),
        ).pack(pady=5)


if __name__ == "__main__":
    Admin_Console()
