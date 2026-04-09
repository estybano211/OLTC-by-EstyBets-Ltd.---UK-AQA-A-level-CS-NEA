from tkinter import Frame, font, Label, Entry, Button


def fetch_text_styles(root):
    """
    Creates and returns a dictionary of named tkinter Font objects.

    Args:
        root: The root Tk window used to bind the font objects.

    Returns:
        dict: A dictionary mapping style names (e.g. 'heading', 'text') to
              tkinter Font instances.
    """
    text_styles = {
        "title": font.Font(
            root=root, family="Times New Roman", size=45, weight="bold", underline=True
        ),
        "heading": font.Font(
            root=root,
            family="Bodoni 72 Smallcaps",
            size=36,
            weight="bold",
            underline=True,
        ),
        "subheading": font.Font(
            root=root, family="Bodoni 72 Smallcaps", size=30, weight="bold"
        ),
        "rules": font.Font(root=root, family="Helvetica", size=20, weight="bold"),
        "text": font.Font(root=root, family="Verdana", size=26),
        "button": font.Font(root=root, family="Tahoma", size=22, weight="bold"),
        "label": font.Font(root=root, family="Didot", size=20),
        "emphasis": font.Font(
            root=root, family="Georgia", size=16, weight="bold", slant="italic"
        ),
    }
    return text_styles


# Colour scheme.
CS = {
    # Windows.
    "pwd_prompt": "#BB8C64",
    "admin": "#BB756D",
    "casino": "#1F6053",
    "rules": "#000000",
    # Labels, entrys and buttons.
    "label_bg": "#D7CBB4",
    "label_text": "#000000",
    "entry_bg": "#FDFEFE",
    "entry_text": "#000000",
    "button_bg": "#F1C40F",
    "button_text": "#000000",
    # Frames backgrounds.
    "top_left": "#D79393",
    "bottom_left": "#E59866",
    "top_right": "#2E7D73",
    "middle_right": "#BCC88B",
    "bottom_right": "#5B2A3C",
    # Widgets.
    "widget_bg": "#A50B5E",
    "widget_text": "#000000",
    # Text.
    "text_bg": "#1A1A1A",
    "text_fg": "#FFFFFF",
    "casino_text": "#E59866",
    # Log panel.
    "log_bg": "#000000",
    "log_fg": "#FFFFFF",
    # Log entry.
    "start_bg": "#243B7A",
    "start_fg": "#FFFFFF",
    "win_bg": "#244D3A",
    "win_fg": "#A8E6C1",
    "loss_bg": "#AE1E1E",
    "loss_fg": "#F2A3A3",
    "tie_bg": "#5C4A10",
    "tie_fg": "#F0d898",
    "thinking_bg": "#3C2A4A",
    "thinking_fg": "#D4B8E8",
    "tournament_bg": "#4A1E38",
    "tournament_fg": "#F4BDD9",
    # Misc.
    "correct": "#13DF00",
    "error": "#FF0000",
    "table_even": "#0C0C0C",
    "table_odd": "#364DE2",
    "separator": "#888888",
    "round_label_bg": "#1A5276",
    "round_label_fg": "#FFFFFF",
}

# Default delay for message logging in seconds.
DELAY = 1.5


# GUI WIDGET PRESET FUNCTIONS


def create_window(root, title, bg_color, is_main_frame=False):
    """
    Creates and configures a standardised Tkinter window.

    Args:
        root (Tk or Toplevel): The Tkinter root window to configure.
        title (str): The title to display in the window title bar.
        bg_color (str): Hex colour string for the window background.
        is_main_frame (bool): If True, creates and returns a packed main
                              Frame alongside the styles dict. If False,
                              returns only the styles dict. Defaults to
                              False.

    Returns:
        tuple[Frame, dict] or dict: When is_main_frame is True, returns
        (main_frame, styles). When False, returns only styles.
    """
    root.configure(bg=bg_color)
    root.title(title)
    width = root.winfo_screenwidth()
    height = root.winfo_screenheight()
    root.geometry(f"{width}x{height}+0+0")
    root.focus_force()

    styles = fetch_text_styles(root)

    if is_main_frame:
        main_frame = Frame(root, bg=bg_color)
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        return main_frame, styles
    else:
        return styles


def preset_label(
    parent, text="", bg=None, fg=None, font=None, relief="raised", bd=2, **kwargs
):
    """
    Create a Label with default styling from CS and raised relief border.

    Args:
        parent (Widget): Parent widget
        text (str): Label text
        bg (str): Override background colour (default: CS["label_bg"])
        fg (str): Override foreground colour (default: CS["label_text"])
        font (Font): Override font (default: fetched from styles)
        relief (str): Border relief style (default: "raised")
        bd (int): Border width (default: 2)
        **kwargs: Additional Label parameters (font, padx, pady, etc.)

    Returns:
        Label widget with styling applied
    """
    bg = bg or CS["label_bg"]
    fg = fg or CS["label_text"]
    style = fetch_text_styles(parent)
    font = font or style["label"]
    return Label(
        parent, text=text, bg=bg, fg=fg, font=font, relief=relief, bd=bd, **kwargs
    )


def preset_button(
    parent, text="", bg=None, fg=None, font=None, relief="raised", bd=2, **kwargs
):
    """
    Create a Button with default styling from CS and raised relief border.

    Args:
        parent (Widget): Parent widget
        text (str): Button text
        bg (str): Override background colour (default: CS["button_bg"])
        fg (str): Override foreground colour (default: CS["button_text"])
        font (Font): Override font (default: fetched from styles)
        relief (str): Border relief style (default: "raised")
        bd (int): Border width (default: 2)
        **kwargs: Additional Button parameters (command, font, width, etc.)

    Returns:
        Button widget with styling applied
    """
    bg = bg or CS["button_bg"]
    fg = fg or CS["button_text"]
    style = fetch_text_styles(parent)
    font = font or style["button"]
    return Button(
        parent, text=text, bg=bg, fg=fg, font=font, relief=relief, bd=bd, **kwargs
    )


def preset_entry(parent, bg=None, fg=None, font=None, **kwargs):
    """
    Create an Entry with default styling from CS.

    Args:
        parent (Widget): Parent widget
        bg (str): Override background colour (default: CS["entry_bg"])
        fg (str): Override foreground colour (default: CS["entry_text"])
        font (Font): Override font (default: fetched from styles)
        **kwargs: Additional Entry parameters (show, width, font, etc.)

    Returns:
        Entry widget with styling applied
    """
    bg = bg or CS["entry_bg"]
    fg = fg or CS["entry_text"]
    style = fetch_text_styles(parent)
    font = font or style["text"]
    return Entry(parent, bg=bg, fg=fg, font=font, **kwargs)


def clear_current_section(self):
    """
    Destroys the currently active section frame if one exists and resets the
    reference to None.

    Args:
        self (object): The parent interface object that holds a 'current_section_frame'
                       attribute.
    """
    if getattr(self, "current_section_frame", None) is not None:
        self.current_section_frame.destroy()
        self.current_section_frame = None


def set_view(self, view_builder):
    """
    Clears the current section frame and builds a new one using the provided
    view builder function. The new frame is packed into the main frame and
    passed to the view builder.

    If the view_builder needs a parameter, lambda can be used to wrap it, e.g.:
    set_view(self, lambda f: self.function(f, param1, param2))
    this allows the view builder to receive the new frame as an argument while also
    passing additional parameters.

    Args:
        self (object): The parent interface object that holds 'main_frame' and
                       'current_section_frame' attributes.
        view_builder (callable): A function that accepts a Frame as its sole
                                 argument and populates it with widgets.
    """
    clear_current_section(self)

    background = getattr(self, "window_bg", None)
    self.current_section_frame = Frame(
        self.main_frame, bg=background if background else self.main_frame.cget("bg")
    )
    self.current_section_frame.pack(expand=True, fill="both")

    view_builder(self.current_section_frame)
