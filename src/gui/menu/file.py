
import os
from src.gui.interfaces import MenuBarItem
from src.common import config, utils
import tkinter as tk

from tkinter.filedialog import askopenfilename, asksaveasfilename
class File(MenuBarItem):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, "File", **kwargs)
        
        self.add_command(
            label="Load Command Book" , command=utils.async_callback(self, File._load_commands)
        )

    @staticmethod
    @utils.run_if_disabled('\n[!] Cannot load command books while Auto Maple is enabled')
    def _load_commands():
        if config.routine.dirty:
            print("TODO")
            return
        
        file_path = askopenfilename(initialdir=os.path.join(config.RESOURCES_DIR, 'command_books'), 
                                    title="Select a command book",
                                    filetypes=[('*.json', '*.json')])
        if file_path:
            config.bot.load_commands(file_path)
    
    def enable_routine_state(self):
        print("AA")
        # self.entryconfig('New Routine', state=tk.NORMAL)
        # self.entryconfig('Save Routine', state=tk.NORMAL)
        # self.entryconfig('Load Routine', state=tk.NORMAL)
    
def get_routines_dir():
    print(f'config.bot: {config.bot.command_book}')
    
    target = os.path.join(config.RESOURCES_DIR, 'routines', config.bot.command_book.name)
    if not os.path.exists(target):
        os.makedirs(target)
    return target


   
