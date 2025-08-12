"""Interfaces that are used by various GUI pages."""

import tkinter as tk
import keyboard as kb
from tkinter import ttk
from src.common import utils


class Frame(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.parent = parent


class Tab(Frame):
    def __init__(self, parent, name, **kwargs):
        super().__init__(parent, **kwargs)
        parent.add(self, text=name)

class LabelFrame(ttk.LabelFrame):
    def __init__(self, parent, name, **kwargs):
        kwargs['text'] = name
        kwargs['labelanchor'] = tk.N
        super().__init__(parent, **kwargs)
        self.parent = parent





class MenuBarItem(tk.Menu):
    def __init__(self, parent, label, **kwargs):
        super().__init__(parent, **kwargs)
        parent.add_cascade(label=label, menu=self)
