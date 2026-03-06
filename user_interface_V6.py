import tkinter as tk
from tkinter import Tk, Label, Button, Frame, Checkbutton, scrolledtext
from gui_helpers_V6 import set_view, fetch_font_settings


class User_Interface:
    """
    Provides the user-facing entry point to the casino application.
    Displays the Terms & Conditions and requires the user to agree before
    granting access to the Casino Interface.
    Automatically creates the database if it does not already exist.
    """

    def __init__(self, show_terms=True):
        """
        Initialises the User Interface window, checks for database existence,
        and starts the application at the Terms & Conditions screen.

        Args:
            show_terms (bool): If True, the Terms & Conditions screen is shown
                               on startup. If False, the casino introduction
                               screen is shown directly.
        """
        self.interface_root = Tk()

        self.interface_root.title("One More Time Casino - User Interface")

        try:
            self.interface_root.attributes("-fullscreen", True)
        except Exception:
            pass

        from database_management_and_logging_V6 import DatabaseManagement

        self.dbm = DatabaseManagement()

        if not self.dbm.check_database_exists():
            self.dbm.create_database()

        self.styles = fetch_font_settings(self.interface_root)

        self.main_frame = Frame(self.interface_root)
        self.main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        self.current_section_frame = None

        if show_terms:
            set_view(self, self.show_terms_and_conditions)
        else:
            set_view(self, self.casino_intro)

        self.interface_root.mainloop()

    def show_terms_and_conditions(self, frame):
        """
        Renders the Terms & Conditions screen. Displays the full T&C text in a
        scrollable, read-only text area. A checkbox must be ticked before the
        Continue button becomes active, at which point the user proceeds to the
        casino introduction screen.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        Label(frame, text="Terms & Conditions", font=self.styles["title"]).pack(pady=10)

        # Create a scrolled text area for long T&C content
        text_area = scrolledtext.ScrolledText(
            frame, wrap=tk.WORD, font=self.styles["terms_and_conditions"]
        )
        text_area.pack(expand=True, fill=tk.BOTH)

        from terms_and_conditions_V6 import terms_and_conditions

        text_area.insert(tk.END, terms_and_conditions())
        text_area.configure(state="disabled")

        agree_var = tk.IntVar()
        tc_window_checkbutton = Checkbutton(
            frame, text="I Agree to the Terms & Conditions", variable=agree_var
        )
        tc_window_checkbutton.pack(pady=5)

        continue_button = Button(
            frame,
            text="Continue",
            state=tk.DISABLED,
            command=lambda: set_view(self, self.casino_intro),
        )
        continue_button.pack(pady=5)

        def on_checkbox_change(*args):
            """
            Callback triggered when the agree checkbox value changes.
            Enables or disables the Continue button based on checkbox state.
            """
            continue_button.config(
                state=tk.NORMAL if agree_var.get() == 1 else tk.DISABLED
            )

        agree_var.trace_add("write", on_checkbox_change)

    def casino_intro(self, frame):
        """
        Renders the casino introduction screen with options to access the
        casino, re-read the Terms & Conditions, or exit the application.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        Label(
            frame, text="Welcome to\nOne More Time Casino", font=self.styles["heading"]
        ).pack(pady=20)

        Button(
            frame,
            text="Access Casino",
            font=self.styles["button"],
            width=30,
            command=self.access_casino,
        ).pack(pady=5)

        Button(
            frame,
            text="Read Terms & Conditions",
            font=self.styles["button"],
            width=30,
            command=lambda: set_view(self, self.show_terms_and_conditions),
        ).pack(pady=5)

        Button(
            frame,
            text="Exit",
            font=self.styles["button"],
            width=30,
            command=self.interface_root.destroy,
        ).pack(pady=5)

    def access_casino(self):
        """
        Opens the Casino Interface in standard user mode by instantiating
        Casino_Interface with administrator=False from casino_interface_V6.
        """
        from casino_interface_V6 import Casino_Interface

        Casino_Interface(False)


if __name__ == "__main__":
    User_Interface(show_terms=False)
