
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

        self.coord_var = tk.StringVar(value="(x, y)")
        self.coord_label = tk.Label(
            self, textvariable=self.coord_var,
            fg='white', bg='black', font=('Consolas', 10)
        )
        self.coord_label.pack(pady=(2, 0))       # 캔버스 바로 아래에 배치

        self.container = None
        self._img = None

    def display_minimap(self):
        """미니맵 이미지와 좌표를 업데이트한다."""
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
            x, y = config.player_pos_ab          # (예: (123, 456))
            self.coord_var.set(f"x: {x}, y: {y}")
        except AttributeError:
            # 값이 아직 없으면 그대로 둠
            pass  

            



        
