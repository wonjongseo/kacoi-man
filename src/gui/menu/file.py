
from src.gui.interfaces import MenuBarItem


class File(MenuBarItem):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, "File", **kwargs)
        
