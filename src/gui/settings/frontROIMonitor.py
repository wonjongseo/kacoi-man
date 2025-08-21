# front_roi_monitor.py
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw
import cv2
import keyboard as kb
from src.common import config

class FrontROIMonitor(ttk.Frame):
    def __init__(self, master, canvas_size=(640, 360), **kwargs):
        super().__init__(master, **kwargs)
        self.canvas_w, self.canvas_h = canvas_size

        self.info = tk.StringVar(value="ROI: -")
        ttk.Label(self, textvariable=self.info).pack(anchor="w", padx=8, pady=(8,4))

        self.canvas = tk.Canvas(self, width=self.canvas_w, height=self.canvas_h, bg="#222")
        self.canvas.pack(fill="both", expand=True, padx=8, pady=8)

        self._photo = None
        self._tick()

    def _tick(self):
        try:
            self._update_view()
        except Exception:
            pass
        self.after(33, self._tick)  # ~30fps

    def _update_view(self):
        cap = getattr(config, "capture", None)
        if cap is None or cap.frame is None:
            self.info.set("게임 설정을 적용해주세요.")
            self.canvas.delete("all")
            return

        frame = cap.frame
        if len(frame.shape) == 3 and frame.shape[2] == 4:
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)
        elif len(frame.shape) == 3 and frame.shape[2] == 3:
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        else:
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)

        H, W = img_rgb.shape[:2]

        if not getattr(config, "player_name_pos", None):
            self.info.set("ROI: player_name_pos 없음")
            self._draw_image_only(img_rgb)
            return

        px, py = config.player_name_pos

        ar = getattr(config, "setting_data", None)
        if not ar or getattr(ar, "attack_range", None) is None:
            self.info.set("게임 설정을 적용해주세요.")
            self._draw_image_only(img_rgb)
            return
        
        front  = config.gui.game_setting.var_rng_front.get()
        back = config.gui.game_setting.var_rng_back.get()
        up = config.gui.game_setting.var_rng_up.get()
        down = config.gui.game_setting.var_rng_down.get()

        if kb.is_pressed("left"):
            facing_left, facing_right = True, False
        elif kb.is_pressed("right"):
            facing_left, facing_right = False, True
        else:
            bot = getattr(config, "bot", None)
            facing_left  = bool(getattr(bot, "left_down", False))  if bot else False
            facing_right = bool(getattr(bot, "right_down", False)) if bot else False

        if not (facing_left ^ facing_right):
            self.info.set("ROI: 정면/방향 불명(왼/오 동시 또는 없음)")
            self._draw_image_only(img_rgb)
            return

        if facing_left:
            x1, x2 = max(0, px - front), px + back
        else:
            x1, x2 = px - back, min(W, px + front)

        y1 = max(0, py - up)
        y2 = min(H, py + down)

        x1, x2, y1, y2 = map(int, (x1, x2, y1, y2))
        self.info.set(f"ROI: x1={x1}, x2={x2}, y1={y1}, y2={y2} | dir={'L' if facing_left else 'R'}")

        self._draw_on_canvas(img_rgb, (x1, y1, x2, y2))

    def _draw_image_only(self, img_rgb):
        self._draw_on_canvas(img_rgb, roi=None)

    def _draw_on_canvas(self, img_rgb, roi=None):
        H, W = img_rgb.shape[:2]
        scale = min(self.canvas_w / W, self.canvas_h / H)
        disp_w = max(1, int(W * scale))
        disp_h = max(1, int(H * scale))

        pil_img = Image.fromarray(img_rgb).resize((disp_w, disp_h), Image.BILINEAR)

        if roi:
            x1, y1, x2, y2 = roi
            draw = ImageDraw.Draw(pil_img)
            sx1 = int(x1 * scale); sy1 = int(y1 * scale)
            sx2 = int(x2 * scale); sy2 = int(y2 * scale)
            draw.rectangle([sx1, sy1, sx2, sy2], outline=(255, 0, 0), width=2)

        self._photo = ImageTk.PhotoImage(pil_img)
        self.canvas.delete("all")
        off_x = (self.canvas_w - disp_w) // 2
        off_y = (self.canvas_h - disp_h) // 2
        self.canvas.create_image(off_x, off_y, anchor="nw", image=self._photo)
