
from src.gui.interfaces import Tab
import tkinter as tk

from src.gui.view.minimap import Minimap

class View(Tab):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, "View", **kwargs)

        self.grid_columnconfigure(0, weight=1)
        # self.grid_columnconfigure(3, weight=1)

        self.minimap = Minimap(self)
        self.minimap.grid(row=0, column=2, sticky=tk.NSEW, padx=10, pady=10)

 