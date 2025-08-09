import threading
import time
from src.common import config,settings
import tkinter as tk
from tkinter import ttk
from src.gui import Edit, View, Menu


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
        self.menu = Menu(self.root)
        self.root.config(menu=self.menu)

        # self.navigation = ttk.Notebook(self.root)
        self.navigation = ttk.Notebook(self.root)
        self.view = View(self.navigation)
        self.edit = Edit(self.navigation)
        
        self.navigation.pack(expand=True, fill='both')
        self.navigation.bind('<<NotebookTabChanged>>', self._resize_window)
        self.root.focus()

    def _resize_window(self, e):
        """Callback to resize entire Tkinter window every time a new Page is selected."""

        nav = e.widget
        curr_id = nav.select()
        nav.nametowidget(curr_id).focus()      # Focus the current Tab
        page = nav.tab(curr_id, 'text')
        if self.root.state() != 'zoomed':
            if page in GUI.RESOLUTIONS:
                self.root.geometry(GUI.RESOLUTIONS[page])
            else:
                self.root.geometry(GUI.RESOLUTIONS['DEFAULT'])
    def set_routine(self, arr):
        self.routine_var.set(arr)

    def clear_routine_info(self):
        """
        Clears information in various GUI elements regarding the current routine.
        Does not clear Listboxes containing routine Components, as that is handled by Routine.
        """

        # self.view.details.clear_info()
        # self.view.status.set_routine('')

        self.edit.minimap.redraw()
        self.edit.routine.commands.clear_contents()
        self.edit.routine.commands.update_display()
        self.edit.editor.reset()

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
        
    def _save_layout(self):
        """Periodically saves the current Layout object."""

        while True:
            if config.layout is not None and settings.record_layout:
                config.layout.save()
            time.sleep(5)





if __name__ == "__main__":
    gui = GUI()
    gui.start()

    # while True:
    #     pass



# python -m src.modules.gui