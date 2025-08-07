import threading
import time
from src.common import config
import tkinter as tk
from tkinter import ttk
from src.gui import View


class GUI:
    DISPLAY_FRAME_RATE = 30
    RESOLUTIONS = {
        'DEFAULT': '800x800',
        'Edit': '1400x800'
    }
    def __init__(self):
        config.gui = self

        self.root = tk.Tk() #새로운 창(window) 생성
        self.root.title("Jonggack Maple")
        self.root.geometry(GUI.RESOLUTIONS['DEFAULT'])
        self.root.resizable(False, False)

        self.routine_var = tk.StringVar() # 탭 간 공유하거나 위젯에 바인딩할 문자열 변수를 하나 생성

        # Build the GUI
        # self.menu = Menu(self.root)
        # self.root.config(menu=self.menu)

        # self.navigation = ttk.Notebook(self.root)
        self.navigation = ttk.Notebook(self.root)
        self.view = View(self.navigation)
        
        self.navigation.pack(expand=True, fill='both')
        # self.navigation.bind('<<NotebookTabChanged>>', self._resize_window)
        self.root.focus()

    def start(self) :

        display_thread = threading.Thread(target=self._display_minimap)
        display_thread.daemon = True
        display_thread.start()

        self.root.mainloop()


    def _display_minimap(self):
        delay = 1 / GUI.DISPLAY_FRAME_RATE
        while True:
            self.view.minimap.display_minimap()
            time.sleep(delay)





if __name__ == "__main__":
    gui = GUI()
    gui.start()

    # while True:
    #     pass



# python -m src.modules.gui