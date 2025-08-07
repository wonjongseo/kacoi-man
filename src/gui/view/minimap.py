
from src.common import config
from src.gui.interfaces import LabelFrame
import cv2
import tkinter as tk
from PIL import ImageTk, Image
class Minimap(LabelFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, 'Minimap', **kwargs)

        self.WIDTH = 400
        self.HEIGHT = 300
        self.canvas = tk.Canvas(self, bg='black',
                                width=self.WIDTH, height=self.HEIGHT,
                                borderwidth=0, highlightthickness=0)
        self.canvas.pack(expand=True, fill='both', padx=5, pady=5)
        self.container = None

    def display_minimap(self) :
        minimap = config.capture.minimap

        if minimap: 
            path = minimap['path']
            player_pos = minimap['player_pos']
            player_name_pos = minimap['player_name_pos']

            img = cv2.cvtColor(minimap['minimap'], cv2.COLOR_BGR2RGB) # 왜 cvtColor 가 뭐야 ?

            height, width, _ = img.shape

            ratio = min(self.WIDTH / width, self.HEIGHT / height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            
            
            if new_height * new_width > 0:
                img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)


            img = ImageTk.PhotoImage(Image.fromarray(img))
            if self.container is None:
                self.container = self.canvas.create_image(self.WIDTH // 2,
                                                          self.HEIGHT // 2,
                                                          image=img, anchor=tk.CENTER)
            else:
                self.canvas.itemconfig(self.container, image=img)
            self._img = img  

            



        
