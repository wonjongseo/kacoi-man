

# # ---------- 3. 물약 매니저 ----------
import time
import cv2
import mss
import numpy as np
import pyautogui
from src.common import config


class PotionManager:
    """
    hp_bar.png / mp_bar.png :  바 안쪽(색이 채워지는 영역)을 포함한
                              '한 덩어리' 템플릿.
    bar_color(BGR)          :  HP=(  0,  0,255)  MP=(255,128, 0) 등
    """
    def __init__(self,interval=0.8):

        self.hp_tpl = cv2.imread('assets/hp_bar.png')
        self.mp_tpl = cv2.imread('assets/mp_bar.png')
        if self.hp_tpl is None or self.mp_tpl is None:
            raise FileNotFoundError("HP/MP 템플릿을 읽지 못했습니다")
        self.hp_roi = None
        self.mp_roi = None
        self.margin_h = 2   # ROI 좌우 여유(픽셀)
        self.margin_v = 0   # ROI 상하 여유(픽셀)
        self.hp_th  = config.setting_data.hp_pct / 100
        self.mp_th  = config.setting_data.mp_pct / 100
        print(f'self.hp_th : {self.hp_th}')
        print(f'self.mp_th : {self.mp_th}')
        
        self.interval = interval
    
    # ──────────────────────────────────────────────
    def _locate_bar_single(self, tpl, label):
        """tpl 위치 한 번 찾고 ROI 반환"""
        with mss.mss() as sct:
            frame = np.array(sct.grab(
                {"left":0, "top":0, "width":config.SCREEN_WIDTH, "height": config.SCREEN_HEIGHT}
            ))[:, :, :3]

        res = cv2.matchTemplate(frame, tpl, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        if max_val < 0.65:
            print(f"[WARN] {label} 템플릿 max_val={max_val:.2f} (0.65 미만)")
            return None                 # 매칭 신뢰도 부족

        tx, ty = max_loc
        h, w   = tpl.shape[:2]

        # ROI = 템플릿 + margin
        x1 = max(0, tx - self.margin_h)
        y1 = max(0, ty - self.margin_v)
        x2 = min(970, tx + w + self.margin_h)
        y2 = min(700, ty + h + self.margin_v)

        

        return (x1, y1, x2, y2)

    # ──────────────────────────────────────────────
    def _ensure_rois(self):
        if self.hp_roi is None:
            self.hp_roi = self._locate_bar_single(self.hp_tpl, 'hp')
        if self.mp_roi is None:
            self.mp_roi = self._locate_bar_single(self.mp_tpl, 'mp')

    # ──────────────────────────────────────────────
    @staticmethod
    def _fill_ratio(roi_bgr, filled_color, tol=60):
        """가운데 1 px 라인에서 target 색상 비율"""
        h, w, _ = roi_bgr.shape
        line = roi_bgr[h//2, :, :]
        diff = np.linalg.norm(line.astype(int) - filled_color, axis=1)
        return (diff < tol).mean()

    # ──────────────────────────────────────────────
    def check(self):
        
        self._ensure_rois()
        if not (self.hp_roi and self.mp_roi):
            return

        with mss.mss() as sct:
            rois = {}
            for name, (x1,y1,x2,y2) in {"hp":self.hp_roi, "mp":self.mp_roi}.items():
                rois[name] = np.array(sct.grab(
                    {"left":x1, "top":y1, "width":x2-x1, "height":y2-y1}
                ))[:, :, :3]

        hp_pct = self._fill_ratio(rois["hp"], (0,0,255))       # HP: 빨강
        mp_pct = self._fill_ratio(rois["mp"], (255,128,0))     # MP: 주황/파랑
        

        if hp_pct < self.hp_th:
            pyautogui.press('delete')
            print(f"[POTION] HP {hp_pct*100:.0f}% → Del 사용")
        if mp_pct < self.mp_th:
            pyautogui.press('end')
            print(f"[POTION] MP {mp_pct*100:.0f}% → End 사용")

    # ──────────────────────────────────────────────
    def loop(self):
        while True:
            if config.enabled is False:
                time.sleep(0.001)
                continue
            self.check()
            time.sleep(self.interval)

