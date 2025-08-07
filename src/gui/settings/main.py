
from src.gui.interfaces import Tab


class Settings(Tab):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, "Settings" , **kwargs)

        self.columnconfigure(0, weight=1)
        self.columnconfigure(3, weight=1)
        


        