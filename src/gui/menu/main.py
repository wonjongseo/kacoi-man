
import tkinter as tk
from src.gui.menu.file import File
from src.gui.menu.update import Update

class Menu(tk.Menu):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)



