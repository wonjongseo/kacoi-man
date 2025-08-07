"""Allows the user to edit routines while viewing each Point's location on the minimap."""

from src.common import config
import inspect
import tkinter as tk

from src.gui.interfaces import Tab, Frame, LabelFrame
from src.gui.view.minimap import Minimap




class Edit(Tab):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, 'Edit', **kwargs)

        self.columnconfigure(0, weight=1)
        self.columnconfigure(4, weight=1)

        # self.record = Record(self)
        # self.record.grid(row=2, column=3, sticky=tk.NSEW, padx=10, pady=10)

        self.minimap = Minimap(self)
        self.minimap.grid(row=0, column=3, sticky=tk.NSEW, padx=10, pady=10)

        # self.status = Status(self)
        # self.status.grid(row=1, column=3, sticky=tk.NSEW, padx=10, pady=10)

        # self.routine = Routine(self)
        # self.routine.grid(row=0, column=1, rowspan=3, sticky=tk.NSEW, padx=10, pady=10)

        # self.editor = Editor(self)
        # self.editor.grid(row=0, column=2, rowspan=3, sticky=tk.NSEW, padx=10, pady=10)





# python -m src.gui.edit.main.py