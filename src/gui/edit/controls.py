import tkinter as tk
from src.common import config
from src.gui.interfaces import Frame


class Controls(Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        self.up_arrow = tk.Button(self, text='▲', width=6, command=self.move('up'))
        self.up_arrow.grid(row=0, column=0)

        self.down_arrow = tk.Button(self, text='▼', width=6, command=self.move('down'))
        self.down_arrow.grid(row=0, column=1, padx=(5, 0))

        self.delete = tk.Button(self, text='\U00002715', width=3, command=self.delete)
        self.delete.grid(row=0, column=2, padx=(5, 0))

        self.new = tk.Button(self, text='\U00002795', width=6, command=self.new)
        self.new.grid(row=0, column=3, padx=(5, 0))

    def move(self, direction) :
        print(f'direction: {direction}')
    
    def delete(self):
        print("deleted")

    def new(self):
        self.parent.parent.editor.create_add_prompt()
        