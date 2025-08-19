"""A module for tracking useful in-game information."""

import cv2
import threading
import ctypes
import mss
import time
import mss.windows
import pygetwindow as gw
import numpy as np
from src.modules.potionManager import PotionManager

from src.common import config, utils, handle_windows
from ctypes import wintypes
import pyautogui
import math
import keyboard as kb




user32 = ctypes.windll.user32
user32.SetProcessDPIAware()


MINIMAP_TOP_BORDER = 0 #5

MINIMAP_BOTTOM_BORDER = 0 #9 

WINDOWED_OFFSET_TOP = 0 #36 # 창 모드일 때 타이틀 바 높이 보정
WINDOWED_OFFSET_LEFT = 0 #10 # 창 모드일 때 좌측 보정

PLAYER_INFO_TOP = 620

MM_TL_TEMPLATE = cv2.imread(utils.resource_path('assets/minimap_topLeft.png'), 0)
MM_BR_TEMPLATE = cv2.imread(utils.resource_path('assets/minimap_bottomRight.png'), 0)

# 이 (MMT_HEIGHT, MMT_WIDTH) 크기만큼은 최소한 확보해야 템플릿 전체가 포함된다
MMT_HEIGHT = max(MM_TL_TEMPLATE.shape[0], MM_BR_TEMPLATE.shape[0])
MMT_WIDTH = max(MM_TL_TEMPLATE.shape[1], MM_BR_TEMPLATE.shape[1])

PLAYER_TEMPLATE = cv2.imread(utils.resource_path('assets/me.png'), 0)
PT_HEIGHT, PT_WIDTH = PLAYER_TEMPLATE.shape


# PLAYER_NAME_TEMPLATE = cv2.imread('assets/charactor.png', 0)
PLAYER_HEIGHT = 70 # 실제 캐릭터 높이

#
# MONSTERS_FOLDER = 'assets/monsters/pigsBitch'
# MONSTER_TEMPLATES = utils.load_templates(MONSTERS_FOLDER)


class Capture:
    def _ensure_templates(self):
        """템플릿을 1회 로드하고 파생 크기 계산 (PyInstaller 대응)."""
        if self._mm_tl_tmpl is None:
            self._mm_tl_tmpl = cv2.imread(utils.resource_path('assets/minimap_topLeft.png'), 0)
        if self._mm_br_tmpl is None:
            self._mm_br_tmpl = cv2.imread(utils.resource_path('assets/minimap_bottomRight.png'), 0)
        if self._player_tmpl is None:
            self._player_tmpl = cv2.imread(utils.resource_path('assets/me.png'), 0)

        # 파생 크기
        th1, tw1 = self._mm_tl_tmpl.shape[:2]
        th2, tw2 = self._mm_br_tmpl.shape[:2]
        self._MMT_HEIGHT = max(th1, th2)
        self._MMT_WIDTH = max(tw1, tw2)

        self._PT_HEIGHT, self._PT_WIDTH = self._player_tmpl.shape[:2]


    def __init__(self):
        """Initializes this Capture object's main thread."""

        config.capture = self

        # 프레임과 미니맵 관련 속성 초기화
        self.frame = None                 # 전체 화면 캡처 이미지
        self.minimap = {}                 # GUI에 전달할 미니맵 정보
        self.minimap_ratio = 1            # 미니맵 가로/세로 비율
        self.minimap_sample = None        # 미니맵 캘리브레이션 샘플

        # mss 스크린샷 객체 초기화 자리 표시
        self.sct = None

        # 캡처 대상 윈도우 영역 (left, top, width, height)
        self.window = { 
            'left' : 0,
            'top' : 0,
            'width' : config.SCREEN_WIDTH, # 1366,
            'height': config.SCREEN_HEIGHT  # 768
        }

        self.ready = False     # GUI가 최초 정보 수신을 기다릴 때 사용
        self.calibrated = False  # 미니맵 위치 보정이 완료되었는지 여부

        # 백그라운드 스레드 생성
        self.thread = threading.Thread(target=self._main)
        self.thread.daemon = True

        # self.potionThread = threading.Thread(target=self._potionMain)
        # self.potionThread.daemon = True
        
        self.window_resized = False
        threading.Thread(target=PotionManager().loop,daemon=True).start()


    def start(self): 
        print('\n[~] Started video capture')
        self.thread.start()
    

    def _main(self):
        """Constantly monitors the player's position and in-game events."""
        """
            목적: Windows 전용 스크린샷 방식에서 불필요한 투명(투명창) 정보를 배제하고 빠르게 화면을 캡처하기 위해 설정
            효과: GDI 호출 시 CAPTUREBLT 플래그를 끔으로써, 예컨대 창 위에 다른 창이 겹쳐 있더라도 비트맵(BLT) 병합 과정을 생략
        """
        mss.windows.CAPTUREBLT = 0

        # try:
        #     self._ensure_templates()
        # except Exception as e:
        #     print(f"[Capture] template load failed: {e}")
        #     return
        

        while self.window_resized is False:
            windows = gw.getWindowsWithTitle(config.TITLE)
            print(f'windows : {windows}')
            
            if windows:
                win = windows[0]
                try:
                    win.moveTo(0, 0)
                    win.resizeTo(config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
                except Exception:
                    pass
                handle_windows.activate_window(win.title)
                config.TITLE = win.title
                print(f"[INFO] '{win.title}' 창 크기 설정 완료.")
                self.window_resized = True
                time.sleep(0.5)
            else:
                print(f"[ERROR] 창을 찾을 수 없음: '{config.TITLE}'")
        while True:
            self.roop_screen()
            time.sleep(0.001)
        # --- NEW: 템플릿 매칭 헬퍼 (몬스터 유무만 빠르게 판단) ---
    def _has_monster(self, gray_area, templates, threshold=0.7):
        if gray_area is None or gray_area.size == 0:
            return False
        h_img, w_img = gray_area.shape[:2]
        for tpl in templates:
            h_tpl, w_tpl = tpl.shape[:2]
            if h_img < h_tpl or w_img < w_tpl:
                continue
            res = cv2.matchTemplate(gray_area, tpl, cv2.TM_CCOEFF_NORMED)
            if np.any(res >= threshold):
                return True
        return False

    # --- NEW: 바라보는 방향 전환 (키업/키다운 + 봇 상태 동기화) ---
    def _face(self, to_dir: str):
        bot = getattr(config, 'bot', None)
        if not bot:
            return
        if to_dir == 'left':
            # 오른쪽 키 해제, 왼쪽 키 누름
            if bot.right_down:
                pyautogui.keyUp('right'); bot.right_down = False
            if not bot.left_down:
                pyautogui.keyDown('left'); bot.left_down = True
        elif to_dir == 'right':
            # 왼쪽 키 해제, 오른쪽 키 누름
            if bot.left_down:
                pyautogui.keyUp('left'); bot.left_down = False
            if not bot.right_down:
                pyautogui.keyDown('right'); bot.right_down = True

    def roop_screen(self):
        handle = user32.FindWindowW(None, config.TITLE)
        rect = wintypes.RECT()
        user32.GetWindowRect(handle, ctypes.pointer(rect))
        rect = (rect.left, rect.top, rect.right, rect.bottom)
        rect = tuple(max(0, x) for x in rect)

        self.window['left'] = rect[0]
        self.window['top'] = rect[1]
        self.window['width'] = max(rect[2] - rect[0], MMT_WIDTH)
        self.window['height'] = max(rect[3] - rect[1], MMT_HEIGHT)
        
        with mss.mss() as self.sct:
            self.frame = self.screenshot()
        if self.frame is None:
            return

        tl, _ = utils.single_match(self.frame, MM_TL_TEMPLATE)
        
        _, br = utils.single_match(self.frame, MM_BR_TEMPLATE)

        mm_tl = (
            tl[0] + MINIMAP_BOTTOM_BORDER,
            tl[1] + MINIMAP_TOP_BORDER
        )
    
        mm_br = (
            max(mm_tl[0] + PT_WIDTH, br[0] - MINIMAP_BOTTOM_BORDER), # 왜 ?
            max(mm_tl[1] + PT_HEIGHT, br[1] - MINIMAP_BOTTOM_BORDER)
        )
        
        self.minimap_ratio = (mm_br[0] - mm_tl[0]) / (mm_br[1] - mm_tl[1]) # 계산식 이해 안된데 ?
        self.minimap_sample = self.frame[mm_tl[1]:mm_br[1], mm_tl[0]:mm_br[0]] # 계산식 이해 안된데 ?
        self.calibrated = True

        MONSTERS_FOLDER = config.setting_data.monster_dir
        MONSTER_TEMPLATES = utils.load_templates(MONSTERS_FOLDER)

        with mss.mss() as self.sct:
            while True:
                if not self.calibrated:
                    break
                self.frame = self.screenshot()
                if self.frame is None:
                    continue
                else:
                    self.frame = self.frame[:PLAYER_INFO_TOP, ::] # 하단의 캐릭터 이름 / 레벨 위치 제거

                # 잘라 놓은 샘플 좌표로 미니맵만 잘라냄
                minimap = self.frame[ mm_tl[1]:mm_br[1], mm_tl[0]:mm_br[0] ]
                player = utils.multi_match(minimap, PLAYER_TEMPLATE, threshold=0.8)
                
                if player:
                    config.player_pos = utils.convert_to_relative(player[0], minimap)
                    config.player_pos_ab = (self.window['left'] + mm_tl[0] + player[0][0], self.window['top']  + mm_tl[1] + player[0][1])
                
                PLAYER_NAME_TEMPLATE =  cv2.imread(config.setting_data.templates.character.name, 0)
                player_name = utils.single_match(self.frame, PLAYER_NAME_TEMPLATE)

                if player_name :
                    x , y = utils.center_from_bounds(*player_name)
                    config.player_name_pos = (x, y - PLAYER_HEIGHT // 2)
                
                # GUI나 다른 모듈이 쓸 수 있도록 패키징
                self.minimap = {
                    'minimap':      minimap,
                    'path':         config.path,
                    'player_pos':   config.player_pos,
                    'player_name_pos':   config.player_name_pos
                }

                if not self.ready:
                    self.ready = True

                time.sleep(0.001)
                
                if config.enabled: 
                    if config.player_name_pos is None : # or config.bot.can_attack != True:
                        continue
                    
                    px, py = config.player_name_pos  # px = X, py = Y
                    front, back, up, down = config.setting_data.attack_range
                    
                    # if config.bot.left_down and config.bot.right_down == False:
                    #     x1, x2 = max(0, px - front), px + back
                    # elif config.bot.right_down and config.bot.left_down == False:
                    #     x1, x2 = px - back, min(self.frame.shape[1], px + front)
                    # else: 
                    #     config.bot.found_monster = False
                    #     continue
                    
                    # y1 = max(0, py - up)
                    # y2 = min(self.frame.shape[0], py + down)

                    # x1, x2, y1, y2 = map(int, (x1, x2, y1, y2))
                    H, W = self.frame.shape[:2]

                    facing_left  = (config.bot.left_down  and not config.bot.right_down)
                    facing_right = (config.bot.right_down and not config.bot.left_down)

                    if not (facing_left or facing_right):
                        # 양쪽 다 누르거나, 아무 방향도 아닐 때는 스킵
                        config.bot.found_monster = False
                        return

                    def rects(px, py, front, back, up, down, facing_left):
                        # (x1, y1, x2, y2) 반환
                        if facing_left:
                            front_rect = (px - front, px + back,  py - up, py + down)   # 왼쪽이 '앞'
                            back_rect  = (px - back,  px + front, py - up, py + down)   # 오른쪽이 '뒤'
                        else:
                            front_rect = (px - back,  px + front, py - up, py + down)   # 오른쪽이 '앞'
                            back_rect  = (px - front, px + back,  py - up, py + down)   # 왼쪽이 '뒤'
                        return front_rect, back_rect

                    def clamp(x1, y1, x2, y2, W, H):
                        x1 = max(0, int(x1)); y1 = max(0, int(y1))
                        x2 = min(W, int(x2)); y2 = min(H, int(y2))
                        return x1, y1, x2, y2

                    # 앞/뒤 영역 산출 + 클램프
                    front_rect, back_rect = rects(px, py, front, back, up, down, facing_left)
                    fx1, fy1, fx2, fy2 = clamp(front_rect[0], front_rect[2], front_rect[1], front_rect[3], W, H)
                    bx1, by1, bx2, by2 = clamp(back_rect[0],  back_rect[2],  back_rect[1],  back_rect[3],  W, H)

                    # ROI 추출 (BGRA → GRAY)
                    front_roi = self.frame[fy1:fy2, fx1:fx2]
                    back_roi  = self.frame[by1:by2, bx1:bx2]

                    if front_roi.size != 0:
                        front_gray = cv2.cvtColor(front_roi, cv2.COLOR_BGRA2GRAY)
                    else:
                        front_gray = None

                    if back_roi.size != 0:
                        back_gray = cv2.cvtColor(back_roi, cv2.COLOR_BGRA2GRAY)
                    else:
                        back_gray = None

                    # --- 핵심 변경: 뒤 먼저 검사 → 있으면 뒤돌아서 공격 ---
                    back_found  = self._has_monster(back_gray,  MONSTER_TEMPLATES, threshold=0.7)
                    front_found = self._has_monster(front_gray, MONSTER_TEMPLATES, threshold=0.7)

                    if back_found:
                        # 방향 전환 후 공격
                        self._face('right' if facing_left else 'left')
                        config.bot.found_monster = True
                        utils.capture_minimap(bx1, by1, bx2, by2)

                        # (선택) 여기서 바로 공격키를 누르고 싶다면 주석 해제
                        # pyautogui.keyDown('z'); time.sleep(0.05); pyautogui.keyUp('z')

                    elif front_found:
                        # 현재 방향 유지하고 공격
                        config.bot.found_monster = True
                        utils.capture_minimap(fx1, fy1, fx2, fy2)

                        # (선택) 즉시 공격:
                        # pyautogui.keyDown('z'); time.sleep(0.05); pyautogui.keyUp('z')

                    else:
                        config.bot.found_monster = False

                    time.sleep(0.001)
                        

                time.sleep(0.001)


    def screenshot(self, delay = 1):
        try:
            return np.array(self.sct.grab(self.window))
        except mss.exception.ScreenShotError:
            print(f'\n[!] Error while taking screenshot, retrying in {delay} second'
                  + ('s' if delay != 1 else ''))
            time.sleep(delay)
            



if __name__ == "__main__":
    capture = Capture()
    capture.start()

    while True:
        pass



# python -m src.modules.capture
