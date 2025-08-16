import threading
import time
from src.common import config
import tkinter as tk
from tkinter import ttk
from src.gui import Monitor, Edit, Settings


class GUI:
    DISPLAY_FRAME_RATE = 30
    RESOLUTIONS = {
        'DEFAULT': '800x800',
        '루틴 설정': '1000x800'
    }
    def __init__(self):
        config.gui = self
        self.root = tk.Tk()
        self.root.title("원가네 헬퍼")
        self.root.geometry(GUI.RESOLUTIONS['DEFAULT'])
        self.root.resizable(False, False)

        self.navigation = ttk.Notebook(self.root)
        self.monitor = Monitor(self.navigation)
        self.game_setting = Settings(self.navigation)
        self.edit = Edit(self.navigation)

        self.navigation.add(self.monitor, text="모니터")
        self.navigation.add(self.game_setting, text="게임 설정")
        self.navigation.add(self.edit, text="루틴 설정")

        self.navigation.pack(expand=True, fill='both')
        self.navigation.bind('<<NotebookTabChanged>>', self._resize_window)
        self.root.focus()

    def _resize_window(self, e):
        nav = e.widget
        curr_id = nav.select()
        page = nav.tab(curr_id, 'text')
        if self.root.state() != 'zoomed':
            self.root.geometry(GUI.RESOLUTIONS.get(page, GUI.RESOLUTIONS['DEFAULT']))

    def start(self) :
        display_thread = threading.Thread(target=self._display_minimap)
        display_thread.daemon = True
        display_thread.start()
        self.root.mainloop()


    def _display_minimap(self):
        delay = 1 / GUI.DISPLAY_FRAME_RATE
        while True:
            self.monitor.minimap.display_minimap()
            self.edit.form_panel.minimap.display_minimap()
            time.sleep(delay)
        

# python -m src.modules.gui