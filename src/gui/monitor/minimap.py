
from src.common import config
from src.gui.interfaces import LabelFrame,Frame
import cv2
import tkinter as tk
from tkinter import ttk
from src.common import config, utils

from PIL import ImageTk, Image

class Minimap(LabelFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, 'Minimap', **kwargs)

        self.WIDTH = 400
        self.HEIGHT = 300

        topbar = Frame(self)
        topbar.pack(fill='x', pady=2)

        group = Frame(self)
        group.pack(anchor="center")

        self.coord_var = tk.StringVar(value="(x, y)")
        self.coord_label = tk.Label(
            group, textvariable=self.coord_var,
            font=('Consolas', 10)
        )
        self.coord_label.pack(side="left",pady=(2, 0),padx= 4) 

        self.canvas = tk.Canvas(self,
                                width=self.WIDTH, height=self.HEIGHT,
                                borderwidth=0, highlightthickness=0)
        self.canvas.pack(expand=True, fill='both', padx=5, pady=5)

        self.container = None
        self._img = None
    
        
    def draw(self, img):
        """Draws IMG onto the Canvas."""

        if config.layout:
            config.layout.draw(img)     # Display the current Layout

        img = ImageTk.PhotoImage(Image.fromarray(img))
        if self.container is None:
            self.container = self.canvas.create_image(self.WIDTH // 2,
                                                      self.HEIGHT // 2,
                                                      image=img, anchor=tk.CENTER)
        else:
            self.canvas.itemconfig(self.container, image=img)
        self._img = img 

    def display_minimap(self):
        """미니맵 이미지와 좌표를 업데이트한다."""
        if config.capture is None:
            return
        
        minimap = config.capture.minimap
        if not minimap:
            return

        # ----- 이미지 처리 -----
        img = cv2.cvtColor(minimap['minimap'], cv2.COLOR_BGR2RGB)
        h, w, _ = img.shape
        ratio = min(self.WIDTH / w, self.HEIGHT / h)
        img = cv2.resize(img, (int(w * ratio), int(h * ratio)), cv2.INTER_AREA)
        img = ImageTk.PhotoImage(Image.fromarray(img))

        # 캔버스에 표시
        if self.container is None:
            self.container = self.canvas.create_image(
                self.WIDTH // 2, self.HEIGHT // 2,
                image=img, anchor=tk.CENTER
            )
        else:
            self.canvas.itemconfig(self.container, image=img)
        self._img = img  # 참조 유지!

        # ----- 좌표 표시 -----
        try:
            x, y = config.player_pos_ab         # (예: (123, 456))
            self.coord_var.set(f"x: {x}, y: {y}")
        except AttributeError:
            # 값이 아직 없으면 그대로 둠
            pass  

            



        
