import argparse
import ast
import io
import os
import re
import tokenize
from pathlib import Path
from typing import Dict, Union, cast

from tkinter import Tk, ttk, Frame, Scrollbar, Text, Button, messagebox, Label, Entry, filedialog
from tkinter.constants import *


__version__ = "0.0.1-alpha"


DEFAULT_IGNORED_FOLDERS = {".git", ".idea", "__pycache__", "venv", "img", "assessment"}
DEFAULT_IGNORED_FILES = {".gitignore", "treegen4gpt.py", "README.md", "LICENSE", "requirements.txt"}
ALLOWED_EXTENSIONS = {".py", ".pyw", ".pyx", ".pyi", ".pyd", ".pxd", ".pxi", ".pyp", ".pyt", ".py3", ".pyde", ".pyst", ".pyz", ".pyc"}

SAVE_FILE_NAME = ".treegen4gpt.save"


def get_arborescence(path: Path, ignored_folders, ignored_files, indent: int = 0) -> str:
    """
    Get the arborescence of the given path, ignoring specified folders and files.

    :param path: Path object representing the root directory.
    :param ignored_folders: Set of folder names to ignore.
    :param ignored_files: Set of file names to ignore.
    :param indent: Integer representing the current indentation level.
    :return: A string representing the arborescence.
    """
    arborescence = ''
    for item in path.iterdir():
        if item.name in ignored_files:
            continue
        if item.is_dir() and item.name not in ignored_folders:
            arborescence += f"{'  ' * indent}- {item.name}\n"
            arborescence += get_arborescence(item, ignored_folders, ignored_files, indent + 1)
        elif item.is_file() and any(item.name.endswith(ext) for ext in ALLOWED_EXTENSIONS):
            arborescence += f"{'  ' * indent}- {item.name}\n"
    return arborescence


def remove_comments_and_docstrings(code: str) -> str:
    """
    Remove comments and docstrings from the given code.

    :param code: A string containing the code.
    :return: A string with comments and docstrings removed.
    """
    code_io = io.StringIO(code)
    clean_code_lines = []

    prev_toktype = tokenize.INDENT
    last_lineno = -1
    last_col = 0

    for tok in tokenize.generate_tokens(code_io.readline):
        token_type = tok.type
        token_string = tok.string
        start_line, start_col = tok.start
        end_line, end_col = tok.end

        if start_line > last_lineno:
            last_col = 0
        if start_col > last_col:
            clean_code_lines.append(" " * (start_col - last_col))

        if token_type == tokenize.COMMENT:
            pass
        elif token_type == tokenize.STRING:
            if prev_toktype != tokenize.INDENT:
                # The triple-quoted string is not a docstring, so include it
                if token_string[:3] not in ('"""', "'''"):
                    clean_code_lines.append(token_string)
        else:
            clean_code_lines.append(token_string)

        prev_toktype = token_type
        last_lineno = end_line
        last_col = end_col

    return ''.join(clean_code_lines)


def remove_function_body(code: str) -> str:
    """
    Remove function bodies from the given code, keeping only the function signatures and docstrings.

    :param code: A string containing the code.
    :return: A string with function bodies removed.
    """
    class FunctionBodyRemover(ast.NodeTransformer):
        def visit_FunctionDef(self, node):
            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(cast(ast.Expr, node.body[0]).value, ast.Str):
                docstring = node.body[0]
                node.body = [docstring, ast.parse("pass").body[0]]
            else:
                node.body = [ast.parse("pass").body[0]]
            return self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node):
            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(cast(ast.Expr, node.body[0]).value, ast.Str):
                docstring = node.body[0]
                node.body = [docstring, ast.parse("pass").body[0]]
            else:
                node.body = [ast.parse("pass").body[0]]
            return self.generic_visit(node)

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        print(f"Error: {e}")
        return code

    tree = FunctionBodyRemover().visit(tree)
    modified_code = ast.unparse(tree)

    return modified_code


def remove_extra_line_jumps(code: str) -> str:
    """
    Remove extra line jumps from the given code.

    :param code: A string containing the code.
    :return: A string with extra line jumps removed.
    """
    code = re.sub(r'\n{3,}', '\n\n', code)
    return code


def prompt_user(message: str) -> str:
    """
    Prompt the user for input with the given message.

    :param message: A string representing the message to display.
    :return: A string representing the user's input.
    """
    while True:
        user_input = input(message)
        if user_input.lower() in {'y', 'n', ''}:
            return user_input.lower()


def write_template(description: str, arborescence: str, selected_files: Dict[Path, bool],
                   remove_comments: Dict[Path, bool], remove_functions: Dict[Path, bool]) -> None:
    """
    Write the template to a file named "template.txt".

    :param description: A string representing the description of the project.
    :param arborescence: A string representing the arborescence of the project.
    :param selected_files: A dictionary mapping file paths to boolean values indicating if the file should be included.
    :param remove_comments: A dictionary mapping file paths to boolean values indicating if comments should be removed.
    :param remove_functions: A dictionary mapping file paths to boolean values indicating if function bodies should be removed.
    """
    for file in selected_files:
        if not selected_files[file]:
            continue

        with file.open('r') as f:
            content = f.read()

        if remove_functions[file]:
            content = remove_function_body(content)

        if remove_comments[file]:
            content = remove_comments_and_docstrings(content)

        content = remove_extra_line_jumps(content)

        arborescence = arborescence.replace(f"- {file.name}\n", f"- {file.name}\n```py\n{content}\n```\n")

    template = f"{description}\n\nHere is there arborescence with most files content (may be reduced or skeleton only):\n{arborescence}\n"

    with open("template.txt", "w") as f:
        f.write(template)

    print("Template generated in template.txt")


def is_parent_ignored(file: Path, ignored_folders: set) -> bool:
    """
    Check if the parent of the given file is in the ignored folders.

    :param file: Path object representing the file.
    :param ignored_folders: Set of folder names to ignore.
    :return: A boolean value indicating if the parent is ignored.
    """
    current = file.parent
    while current != Path('.'):
        if current.name in ignored_folders:
            return True
        current = current.parent
    return False


def get_user_settings(saved_settings=None) -> tuple:
    """
    Get user settings for generating the template.

    :param saved_settings: A tuple containing saved settings, if available.
    :return: A tuple containing the user's settings.
    """
    description = input("Enter the description: ")

    if saved_settings:
        ignored_folders = saved_settings[4]
        ignored_files = saved_settings[5]
    else:
        ignored_folders_input = input(f"Enter ignored folders (comma-separated, default: {', '.join(DEFAULT_IGNORED_FOLDERS)}): ")
        ignored_folders = set(ignored_folders_input.split(',')) if ignored_folders_input else DEFAULT_IGNORED_FOLDERS

        ignored_files_input = input(f"Enter ignored files (comma-separated, default: {', '.join(DEFAULT_IGNORED_FILES)}): ")
        ignored_files = set(ignored_files_input.split(',')) if ignored_files_input else DEFAULT_IGNORED_FILES

    if saved_settings:
        selected_files = saved_settings[1].copy()
        remove_comments = saved_settings[2].copy()
        remove_functions = saved_settings[3].copy()
    else:
        selected_files = {}
        remove_comments = {}
        remove_functions = {}

    for file in Path('.').rglob('*.py'):
        if is_parent_ignored(file, ignored_folders) or file.name in ignored_files:
            continue
        if file not in selected_files:
            include = prompt_user(f"Include {file}? (y/n): ")
            if include == 'y':
                selected_files[file] = True
                remove_comments[file] = prompt_user(f"Remove comments and docstrings from {file}? (y/n): ") == 'y'
                remove_functions[file] = prompt_user(f"Remove function bodies from {file}? (y/n): ") == 'y'
            else:
                selected_files[file] = False
        elif not selected_files[file]:
            del selected_files[file]
            del remove_comments[file]
            del remove_functions[file]

    return description, selected_files, remove_comments, remove_functions, ignored_folders, ignored_files


def save_settings(description: str, selected_files: Dict[Path, bool],
                  remove_comments: Dict[Path, bool], remove_functions: Dict[Path, bool],
                  ignored_folders, ignored_files) -> None:
    """
    Save the user's settings to a file named ".treegen4gpt.save".

    :param description: A string representing the description of theproject.
    :param selected_files: A dictionary mapping file paths to boolean values indicating if the file should be included.
    :param remove_comments: A dictionary mapping file paths to boolean values indicating if comments should be removed.
    :param remove_functions: A dictionary mapping file paths to boolean values indicating if function bodies should be removed.
    :param ignored_folders: Set of folder names to ignore.
    :param ignored_files: Set of file names to ignore.
    """
    with open(SAVE_FILE_NAME, "w") as f:
        description_save = description.replace('\n', '<newline>')
        f.write(f"{description_save}\n")
        f.write(f"{len(selected_files)}\n")
        for file in selected_files:
            if file in remove_comments and file in remove_functions:
                f.write(f"{file} {selected_files[file]} {remove_comments[file]} {remove_functions[file]}\n")

        # Add these lines to save ignored_folders and ignored_files in the config file
        f.write(', '.join(ignored_folders) + '\n')
        f.write(', '.join(ignored_files) + '\n')


def load_settings() -> Union[tuple, None]:
    """
    Load settings from the ".treegen4gpt.save" file, if it exists.

    :return: A tuple containing the loaded settings, or None if the file does not exist.
    """
    if not Path(SAVE_FILE_NAME).exists():
        return None

    with open(SAVE_FILE_NAME, "r") as f:
        description = f.readline().strip()
        # Replace the newline placeholder with actual newlines to allow multiline description
        description = description.replace('<newline>', '\n')
        num_files = int(f.readline().strip())
        selected_files = {}
        remove_comments = {}
        remove_functions = {}
        for i in range(num_files):
            line = f.readline().strip().split()
            if len(line) >= 4:
                file_path = Path(line[0])
                selected_files[file_path] = line[1] == "True"
                remove_comments[file_path] = line[2] == "True"
                remove_functions[file_path] = line[3] == "True"

        ignored_folders_line = f.readline().strip()
        ignored_files_line = f.readline().strip()

        ignored_folders = set(ignored_folders_line.split(', ')) if ignored_folders_line else DEFAULT_IGNORED_FOLDERS
        ignored_files = set(ignored_files_line.split(', ')) if ignored_files_line else DEFAULT_IGNORED_FILES

    return description, selected_files, remove_comments, remove_functions, ignored_folders, ignored_files


class App:
    """
    The main application class for the Tree Gen 4 GPT GUI.
    """

    def __init__(self, master):
        """
        Initialize the application with the given Tkinter master widget.

        :param master: The Tkinter master widget.
        """
        self.master = master
        self.master.title("TreeGen4GPT")
        self.master.configure(bg="#f0f0f0")

        self.master.columnconfigure(1, weight=1)
        self.master.rowconfigure(3, weight=1)

        # Description label and entry
        self.description_label = Label(self.master, text="Description:", bg="#f0f0f0")
        self.description_label.grid(row=0, column=0, sticky=W, padx=10, pady=10)

        self.description_frame = Frame(self.master)
        self.description_frame.grid(row=0, column=1, sticky=W+E+N+S, padx=10, pady=10)

        self.description_scrollbar = Scrollbar(self.description_frame, orient="vertical")
        self.description_scrollbar.pack(side=RIGHT, fill=Y)

        self.description_entry = Text(self.description_frame, width=50, height=6, wrap=WORD, yscrollcommand=self.description_scrollbar.set)
        self.description_entry.pack(side=LEFT, fill=BOTH, expand=True)

        self.description_scrollbar.config(command=self.description_entry.yview)

        # Ignored folders label and entry
        self.ignored_folders_label = Label(self.master, text="Ignored Folders:", bg="#f0f0f0")
        self.ignored_folders_label.grid(row=1, column=0, sticky=W, padx=10, pady=10)

        self.ignored_folders_entry = Entry(self.master, width=50)
        self.ignored_folders_entry.insert(0, ', '.join(DEFAULT_IGNORED_FOLDERS))
        self.ignored_folders_entry.grid(row=1, column=1, sticky=W+E, padx=10, pady=10)

        # Ignored files label and entry
        self.ignored_files_label = Label(self.master, text="Ignored Files:", bg="#f0f0f0")
        self.ignored_files_label.grid(row=2, column=0, sticky=W, padx=10, pady=10)

        self.ignored_files_entry = Entry(self.master, width=50)
        self.ignored_files_entry.insert(0, ', '.join(DEFAULT_IGNORED_FILES))
        self.ignored_files_entry.grid(row=2, column=1, sticky=W+E, padx=10, pady=10)

        # Treeview for displaying the arborescence and settings
        self.tree = ttk.Treeview(self.master, columns=("Include", "Remove Comments", "Remove Functions"))
        self.tree.heading("#0", text="Arborescence")
        self.tree.heading("Include", text="Include")
        self.tree.heading("Remove Comments", text="Remove Comments")
        self.tree.heading("Remove Functions", text="Remove Functions")
        self.tree.column("#0", width=300)
        self.tree.column("Include", width=60)
        self.tree.column("Remove Comments", width=120)
        self.tree.column("Remove Functions", width=120)
        self.tree.grid(row=3, column=0, columnspan=2, sticky=W + E + N + S, padx=10, pady=10)

        self.tree.tag_configure("included", background="lightblue")
        self.tree.tag_configure("not_included", background="white")
        self.tree.tag_configure("directory", background="white")
        self.tree.bind("<Button-1>", self.on_treeview_click)

        # Buttons for generating the template and managing settings
        self.button_frame = Frame(self.master)
        self.button_frame.grid(row=4, column=0, columnspan=2, pady=10)

        self.generate_button = Button(self.button_frame, text="Generate Template", command=self.generate_template)
        self.generate_button.pack(side=LEFT, padx=(0, 5))

        self.reload_button = Button(self.button_frame, text="Reload", command=self.populate_tree)
        self.reload_button.pack(side=LEFT, padx=(5, 5))

        self.load_settings_button = Button(self.button_frame, text="Load Settings", command=self.load_settings)
        self.load_settings_button.pack(side=LEFT, padx=(5, 5))

        self.save_settings_button = Button(self.button_frame, text="Save Settings", command=self.save_settings)
        self.save_settings_button.pack(side=LEFT, padx=(5, 0))

        self.change_dir_button = Button(self.button_frame, text="Change Directory", command=self.change_directory, bg="gray", fg="white")
        self.change_dir_button.pack(side=LEFT, padx=(5, 0))

        self.reset_button = Button(self.button_frame, text="Reset", command=self.reset_settings, bg="red", fg="white")
        self.reset_button.pack(side=LEFT, padx=(5, 0))

        self.populate_tree()

    @staticmethod
    def is_parent_ignored(file: Path, ignored_folders: set) -> bool:
        """
        Check if the parent of the given file is in the ignored folders.

        :param file: Path object representing the file.
        :param ignored_folders: Set of folder names to ignore.
        :return: A boolean value indicating if the parent is ignored.
        """
        current = file.parent
        while current != Path('.'):
            if current.name in ignored_folders:
                return True
            current = current.parent
        return False

    def populate_tree(self):
        """
        Populate the treeview with the current arborescence, taking into account the ignored folders and files.
        """
        current_state = self.get_tree_state()
        self.tree.delete(*self.tree.get_children())
        ignored_folders = set(self.ignored_folders_entry.get().split(', '))
        ignored_files = set(self.ignored_files_entry.get().split(', '))
        self.add_files_to_tree(Path('.'), '', ignored_folders, ignored_files)
        self.set_tree_state(current_state)

    def add_files_to_tree(self, path, parent, ignored_folders, ignored_files):
        """
        Add files and folders to the treeview recursively.

        :param path: Path object representing the current directory.
        :param parent: The parent treeview item.
        :param ignored_folders: Set of folder names to ignore.
        :param ignored_files: Set of file names to ignore.
        """
        for item in path.iterdir():
            if item.name in ignored_files:
                continue
            if item.is_dir() and item.name not in ignored_folders:
                folder_iid = self.tree.insert(parent, "end", text=item.name, tags=("directory",))
                self.add_files_to_tree(item, folder_iid, ignored_folders, ignored_files)
            elif item.is_file() and any(item.name.endswith(ext) for ext in ALLOWED_EXTENSIONS):
                file_iid = self.tree.insert(parent, "end", text=item.name, tags=(str(item),))
                self.tree.set(file_iid, "Include", "")
                self.tree.set(file_iid, "Remove Comments", "No")
                self.tree.set(file_iid, "Remove Functions", "No")

    def reset_tree_items(self):
        """
        Reset the treeview items to their default values.
        """
        for item in self.tree.get_children():
            self.reset_tree_item(item)

    def reset_tree_item(self, item):
        """
        Reset the given treeview item to its default value.

        :param item: The treeview item.
        """
        item_text = self.tree.item(item, "text")
        item_tags = self.tree.item(item, "tags")

        if item_text.endswith(".py"):
            self.tree.item(item, tags=(str(item_tags[0]), "not_included"))
            self.tree.set(item, "Include", "")
            self.tree.set(item, "Remove Comments", "No")
            self.tree.set(item, "Remove Functions", "No")

        for child in self.tree.get_children(item):
            self.reset_tree_item(child)

    def on_treeview_click(self, event):
        """
        Handle clicks on the treeview items.

        :param event: The Tkinter event object.
        """
        item = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)

        if not item or column not in {"#1", "#2", "#3"} or "directory" in self.tree.item(item, "tags"):
            return

        value = self.tree.set(item, column)
        item_tags = self.tree.item(item, "tags")
        file_path_tag = item_tags[0]

        if column == "#1":
            new_value = "Included" if value == "" else ""
            tag = "included" if new_value == "Included" else "not_included"
            self.tree.item(item, tags=(file_path_tag, tag))
        else:
            new_value = "Yes" if value == "No" else "No"

        self.tree.set(item, column, new_value)

    def generate_template(self):
        """
        Generate the template based on the user's settings and write it to a file named "template.txt".
        """
        description = self.description_entry.get("1.0", END).strip()
        selected_files = {}
        remove_comments = {}
        remove_functions = {}

        for item in self.tree.get_children():
            self.process_tree_item(item, selected_files, remove_comments, remove_functions)

        ignored_folders = set(self.ignored_folders_entry.get().split(', '))
        ignored_files = set(self.ignored_files_entry.get().split(', '))
        arborescence = get_arborescence(Path('.'), ignored_folders, ignored_files)
        write_template(description, arborescence, selected_files, remove_comments, remove_functions)
        messagebox.showinfo("Success", "Template generated in template.txt")

    def process_tree_item(self, item, selected_files, remove_comments, remove_functions):
        """
        Process the treeview item and update the dictionaries with the user's settings.

        :param item: The treeview item.
        :param selected_files: A dictionary mapping file paths to boolean values indicating if the file should be included.
        :param remove_comments: A dictionary mapping file paths to boolean values indicating if comments should be removed.
        :param remove_functions: A dictionary mapping file paths to boolean values indicating if function bodies should be removed.
        """
        item_text = self.tree.item(item, "text")
        item_values = self.tree.item(item, "values")
        item_tags = self.tree.item(item, "tags")

        if item_text.endswith(".py"):
            file_path = Path(item_tags[0])
            selected_files[file_path] = item_values[0] == "Included"
            remove_comments[file_path] = item_values[1] == "Yes"
            remove_functions[file_path] = item_values[2] == "Yes"

        for child in self.tree.get_children(item):
            self.process_tree_item(child, selected_files, remove_comments, remove_functions)

    def get_tree_state(self):
        """
        Get the current state of the treeview.

        :return: A dictionary representing the current state of the treeview.
        """
        state = {}
        for item in self.tree.get_children():
            self.get_tree_item_state(item, state)
        return state

    def get_tree_item_state(self, item, state):
        """
        Get the state of the given treeview item and update the state dictionary.

        :param item: The treeview item.
        :param state: A dictionary representing the current state of the treeview.
        """
        item_text = self.tree.item(item, "text")
        item_values = self.tree.item(item, "values")
        item_tags = self.tree.item(item, "tags")

        if item_text.endswith(".py"):
            file_path = Path(item_tags[0])
            state[file_path] = {
                "Include": item_values[0],
                "Remove Comments": item_values[1],
                "Remove Functions": item_values[2],
            }

        for child in self.tree.get_children(item):
            self.get_tree_item_state(child, state)

    def set_tree_state(self, state):
        """
        Set the state of the treeview based on the given state dictionary.

        :param state: A dictionary representing the state of the treeview.
        """
        for item in self.tree.get_children():
            self.set_tree_item_state(item, state)

    def set_tree_item_state(self, item, state):
        """
        Set the state of the given treeview item based on the given state dictionary.

        :param item: The treeview item.
        :param state: A dictionary representing the state of the treeview.
        """
        item_text = self.tree.item(item, "text")
        item_tags = self.tree.item(item, "tags")

        # If the item is a Python file, update its state based on the state dictionary
        if item_text.endswith(".py"):
            file_path = Path(item_tags[0])
            if file_path in state:
                include_value = state[file_path]["Include"]
                remove_comments_value = state[file_path]["Remove Comments"]
                remove_functions_value = state[file_path]["Remove Functions"]

                tag = "included" if include_value == "Included" else "not_included"
                self.tree.item(item, tags=(str(file_path), tag))
                self.tree.set(item, "Include", include_value)
                self.tree.set(item, "Remove Comments", remove_comments_value)
                self.tree.set(item, "Remove Functions", remove_functions_value)

        # Recursively set the state for child items
        for child in self.tree.get_children(item):
            self.set_tree_item_state(child, state)

    def load_settings(self):
        """
        Load settings from the ".pyarborescaper.save" file, if it exists, and apply them to the treeview.
        """
        saved_settings = load_settings()

        if saved_settings:
            description, selected_files, remove_comments, remove_functions, ignored_folders, ignored_files = saved_settings
            self.description_entry.delete("1.0", END)
            self.description_entry.insert("1.0", description)

            # Update the ignored_folders_entry and ignored_files_entry with the loaded values
            self.ignored_folders_entry.delete(0, END)
            self.ignored_folders_entry.insert(0, ', '.join(ignored_folders))
            self.ignored_files_entry.delete(0, END)
            self.ignored_files_entry.insert(0, ', '.join(ignored_files))

            # Apply the loaded settings to the treeview
            for item in self.tree.get_children():
                self.load_tree_item(item, selected_files, remove_comments, remove_functions)
        else:
            messagebox.showwarning("Warning", "No saved settings found.")

    def load_tree_item(self, item, selected_files, remove_comments, remove_functions):
        """
        Load the settings for the given treeview item based on the loaded settings.

        :param item: The treeview item.
        :param selected_files: A dictionary mapping file paths to boolean values indicating if the file should be included.
        :param remove_comments: A dictionary mapping file paths to boolean values indicating if comments should be removed.
        :param remove_functions: A dictionary mapping file paths to boolean values indicating if function bodies should be removed.
        """
        item_text = self.tree.item(item, "text")
        item_tags = self.tree.item(item, "tags")
        if item_text.endswith(".py"):
            file_path = Path(item_tags[0])
            if file_path in selected_files:
                tag = "included" if selected_files[file_path] else "not_included"
                self.tree.item(item, tags=(str(file_path), tag))
                self.tree.set(item, "Include", "Included" if selected_files[file_path] else "")
                self.tree.set(item, "Remove Comments", "Yes" if remove_comments[file_path] else "No")
                self.tree.set(item, "Remove Functions", "Yes" if remove_functions[file_path] else "No")

        # Recursively load settings for child items
        for child in self.tree.get_children(item):
            self.load_tree_item(child, selected_files, remove_comments, remove_functions)

    def save_settings(self):
        """
        Save the current settings to the ".pyarborescaper.save" file.
        """
        description = self.description_entry.get("1.0", END).strip()
        selected_files = {}
        remove_comments = {}
        remove_functions = {}

        # Retrieve the settings from the treeview
        for item in self.tree.get_children():
            self.process_tree_item(item, selected_files, remove_comments, remove_functions)

        ignored_folders = set(self.ignored_folders_entry.get().split(', '))
        ignored_files = set(self.ignored_files_entry.get().split(', '))
        save_settings(description, selected_files, remove_comments, remove_functions, ignored_folders, ignored_files)
        messagebox.showinfo("Success", "Settings saved.")

    def change_directory(self):
        """
        Change the current working directory using a directory dialog. Reset the files context menu and repopulate the treeview.
        Also has a disclaimer dialog to warn the user that changing the directory will reset files settings.
        """
        new_dir = filedialog.askdirectory()
        if new_dir and messagebox.askyesno("Confirm", "Are you sure you want to change the directory? This will reset the files settings."):
            os.chdir(new_dir)
            self.reset_tree_items()
            self.populate_tree()

    def reset_settings(self):
        """
        Reset the settings to their default values with a confirmation dialog.
        """
        if messagebox.askyesno("Confirm Reset", "Are you sure you want to reset the settings to their default values?"):
            self.description_entry.delete("1.0", END)

            self.ignored_folders_entry.delete(0, END)
            self.ignored_folders_entry.insert(0, ', '.join(DEFAULT_IGNORED_FOLDERS))

            self.ignored_files_entry.delete(0, END)
            self.ignored_files_entry.insert(0, ', '.join(DEFAULT_IGNORED_FILES))

            self.reset_tree_items()

            self.populate_tree()


def run_cli():
    """
    Run the command-line interface version of the TreeGen4GPT.
    """
    saved_settings = load_settings()

    if saved_settings:
        use_saved_settings = prompt_user(f"Do you want to use the saved settings? (y/n): ")
        if use_saved_settings == 'y':
            description, selected_files, remove_comments, remove_functions, ignored_folders, ignored_files = saved_settings
        else:
            description, selected_files, remove_comments, remove_functions, ignored_folders, ignored_files = get_user_settings(saved_settings)
    else:
        description, selected_files, remove_comments, remove_functions, ignored_folders, ignored_files = get_user_settings()

    arborescence = get_arborescence(Path('.'), ignored_folders, ignored_files)
    print("\nArborescence:\n" + arborescence)

    write_template(description, arborescence, selected_files, remove_comments, remove_functions)

    save_choice = prompt_user("Do you want to save these settings? (y/n): ")
    if save_choice == 'y':
        save_settings(description, selected_files, remove_comments, remove_functions, ignored_folders, ignored_files)


def main():
    """
    The main function that runs the TreeGen4GPT.
    """
    parser = argparse.ArgumentParser(description="TreeGen4GPT")
    parser.add_argument("--cli", action="store_true", help="Run the program without the graphical user interface")
    parser.add_argument("--dir", type=str, help="Specify the working directory")
    args = parser.parse_args()

    if args.dir:
        os.chdir(args.dir)

    if args.cli:
        run_cli()
    else:
        root = Tk()
        app = App(root)
        root.mainloop()
        del app


if __name__ == "__main__":
    main()
