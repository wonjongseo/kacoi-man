import time
import cv2
import mss
import numpy as np
import pyautogui
from src.common import config, utils, default_value as df


class PotionManager:
    def __init__(self, interval=0.8):
        self.hp_tpl = cv2.imread(utils.resource_path('assets/hp_bar.png'))
        self.mp_tpl = cv2.imread(utils.resource_path('assets/mp_bar.png'))
        if self.hp_tpl is None or self.mp_tpl is None:
            raise FileNotFoundError("HP/MP 템플릿을 읽지 못했습니다")
        self.hp_roi = None
        self.mp_roi = None
        self.margin_h = 2
        self.margin_v = 0
        self.hp_th = config.setting_data.hp_pct / 100
        self.mp_th = config.setting_data.mp_pct / 100
        self.interval = interval
        self.hp_key = getattr(config.setting_data, 'hp_key', df.HP_KEY)
        self.mp_key = getattr(config.setting_data, 'mp_key', df.MP_KEY)


        self.post_check_delay = 0.18
        self.min_increase_hp = 0.02
        self.min_increase_mp = 0.02
        self.fail_limit = 3
        self.hp_fail = 0
        self.mp_fail = 0
        self.hp_out = False
        self.mp_out = False
        self._hp_out_reported = False
        self._mp_out_reported = False


    def _color_ratio_hsv(self, roi_bgr, color: str, sat_min=80, val_min=60):
        h, w, _ = roi_bgr.shape
        if h == 0 or w == 0:
            return 0.0
        line = roi_bgr[h // 2: h // 2 + 1, :, :]
        hsv = cv2.cvtColor(line, cv2.COLOR_BGR2HSV)
        H = hsv[:, :, 0]; S = hsv[:, :, 1]; V = hsv[:, :, 2]
        sv_mask = (S >= sat_min) & (V >= val_min)
        if color == 'red':
            m1 = (H >= 0) & (H <= 10)
            m2 = (H >= 170) & (H <= 179)
            mask = (m1 | m2) & sv_mask
        elif color == 'blue':
            mask = (H >= 100) & (H <= 130) & sv_mask
        else:
            mask = np.zeros_like(H, dtype=bool)
        return mask.mean()


    def _locate_bar_single(self, tpl, label, expected_color=None, search_rect=None, max_tries=5):
        if search_rect is None:
            left, top = 0, 0
            width, height = config.SCREEN_WIDTH, config.SCREEN_HEIGHT
        else:
            left, top, width, height = search_rect

        with mss.mss() as sct:
            frame = np.array(sct.grab({"left": left, "top": top, "width": width, "height": height}))[:, :, :3]

        res = cv2.matchTemplate(frame, tpl, cv2.TM_CCOEFF_NORMED)
        th = 0.65

        h, w = tpl.shape[:2]
        tries = 0
        while tries < max_tries:
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            if max_val < th:
                return None

            tx, ty = max_loc
            x1 = max(0, tx - self.margin_h)
            y1 = max(0, ty - self.margin_v)
            x2 = min(width, tx + w + self.margin_h)
            y2 = min(height, ty + h + self.margin_v)

            roi = frame[y1:y2, x1:x2]
            ok = True
            if expected_color in ('red', 'blue'):
                ratio = self._color_ratio_hsv(roi, expected_color)
                if ratio < 0.18:
                    ok = False

            if ok:
                return (left + x1, top + y1, left + x2, top + y2)

            res[ty:ty + h, tx:tx + w] = 0
            tries += 1

        return None


    def _ensure_rois(self):
        if self.mp_roi is None:
            self.mp_roi = self._locate_bar_single(self.mp_tpl, 'mp', expected_color='blue')
        if self.hp_roi is None:
            if self.mp_roi:
                mp_x1, _, _, _ = self.mp_roi
                search_rect = (0, 0, max(10, mp_x1), config.SCREEN_HEIGHT)
            else:
                search_rect = None
            self.hp_roi = self._locate_bar_single(self.hp_tpl, 'hp', expected_color='red', search_rect=search_rect)


    def _grab_rois(self):
        with mss.mss() as sct:
            out = {}
            for name, roi in (("hp", self.hp_roi), ("mp", self.mp_roi)):
                if not roi:
                    out[name] = None
                    continue
                x1, y1, x2, y2 = roi
                out[name] = np.array(sct.grab(
                    {"left": x1, "top": y1, "width": x2 - x1, "height": y2 - y1}
                ))[:, :, :3]
        return out


    def _fill_ratio_color(self, roi_bgr, color: str):
        return self._color_ratio_hsv(roi_bgr, color)


    def _try_consume(self, bar: str, key: str, before_pct: float) -> bool:
        pyautogui.press(key)
        time.sleep(self.post_check_delay)
        rois_after = self._grab_rois()
        if bar == 'hp':
            after_pct = self._fill_ratio_color(rois_after["hp"], 'red') if rois_after["hp"] is not None else before_pct
            return (after_pct - before_pct) >= self.min_increase_hp
        else:
            after_pct = self._fill_ratio_color(rois_after["mp"], 'blue') if rois_after["mp"] is not None else before_pct
            return (after_pct - before_pct) >= self.min_increase_mp


    def check(self):
        self._ensure_rois()
        if not (self.hp_roi and self.mp_roi):
            return

        rois = self._grab_rois()
        if rois["hp"] is None or rois["mp"] is None:
            return

        hp_pct = self._fill_ratio_color(rois["hp"], 'red')
        mp_pct = self._fill_ratio_color(rois["mp"], 'blue')

        # ----- HP -----
        if hp_pct < self.hp_th:
            ok = self._try_consume('hp', self.hp_key, hp_pct)
            if ok:
                if self.hp_out:
                    print("[POTION] HP 포션 재사용 확인 → 상태 해제")
                self.hp_out = False
                self._hp_out_reported = False
                self.hp_fail = 0
                print(f"[POTION] HP {hp_pct*100:.0f}% → {self.hp_key} 사용(성공)")
            else:
                self.hp_fail += 1
                print(f"[POTION] HP {hp_pct*100:.0f}% → {self.hp_key} 사용(증가 없음, 실패 {self.hp_fail}/{self.fail_limit})")
                if self.hp_fail >= self.fail_limit:
                    self.hp_fail = 0
                    self.hp_out = True
                    if not self._hp_out_reported:
                        print("[POTION] HP 포션 없음으로 판단(쿨다운 없이 계속 재시도)")
                        self._hp_out_reported = True

        # ----- MP -----
        if mp_pct < self.mp_th:
            ok = self._try_consume('mp', self.mp_key, mp_pct)
            if ok:
                if self.mp_out:
                    print("[POTION] MP 포션 재사용 확인 → 상태 해제")
                self.mp_out = False
                self._mp_out_reported = False
                self.mp_fail = 0
                print(f"[POTION] MP {mp_pct*100:.0f}% → {self.mp_key} 사용(성공)")
            else:
                self.mp_fail += 1
                print(f"[POTION] MP {mp_pct*100:.0f}% → {self.mp_key} 사용(증가 없음, 실패 {self.mp_fail}/{self.fail_limit})")
                if self.mp_fail >= self.fail_limit:
                    self.mp_fail = 0
                    self.mp_out = True
                    if not self._mp_out_reported:
                        print("[POTION] MP 포션 없음으로 판단(쿨다운 없이 계속 재시도)")
                        self._mp_out_reported = True


    def loop(self):
        while True:
            if config.enabled is False:
                time.sleep(0.001)
                continue
            self.check()
            time.sleep(self.interval)
