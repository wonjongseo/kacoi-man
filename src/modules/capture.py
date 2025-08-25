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
        
        self.last_attack_t = 0.0
        self.attack_interval = 0.14   # 공격 최소 간격(초) - 필요시 0.10~0.20 튜닝
        config.attack_in_capture = True  # 캡처 스레드가 공격을 담당


        self.window_resized = False
        threading.Thread(target=PotionManager().loop,daemon=True).start()

    def _attack_immediate(self, dir_hint: str):
        bot = getattr(config, 'bot', None)
        if not bot or not config.enabled:
            return
        if bot.is_climbing or bot.up_down:   # 사다리 최우선
            return

        now = time.time()
        if now - self.last_attack_t < self.attack_interval:
            return

        # 방향 보정
        if dir_hint == 'back':
            if bot.right_down and not bot.left_down:
                bot.face('left')
            elif bot.left_down and not bot.right_down:
                bot.face('right')
            else:
                bot.face('left' if (bot.prev_direction == 'right') else 'right')
        else:
            if not bot.left_down and not bot.right_down:
                bot.face(bot.prev_direction or 'right')

        # 탭 공격(락 내부)
        bot.tap_attack(dur=0.01)
        self.last_attack_t = now
        bot.mark_attack()  # ← 공격 모션 진행 중 표시
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
        while not (config.macro_shutdown_evt and config.macro_shutdown_evt.is_set()):
            self.roop_screen()
            time.sleep(0.001)
    def stop(self):
        if config.macro_shutdown_evt:
            config.macro_shutdown_evt.set()
        # 필요시 조인
        # if self.thread and self.thread.is_alive():
        #     self.thread.join(timeout=2)
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
            while not (config.macro_shutdown_evt and config.macro_shutdown_evt.is_set()):
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
                

                config.margin_tl = self.window['left'] + mm_tl[0]
                config.margin_tr = self.window['top']  + mm_tl[1] 


                if player:
                    config.player_pos_ab = (config.margin_tl + player[0][0], config.margin_tr + player[0][1])

                frame_h, frame_w = self.frame.shape[:2]
                cropped_frame = self.frame[0:frame_h+100, :]
                PLAYER_NAME_TEMPLATE =  cv2.imread(config.setting_data.templates.character.name, 0)
                player_name = utils.single_match(cropped_frame, PLAYER_NAME_TEMPLATE)

                if player_name :
                    x , y = utils.center_from_bounds(*player_name)
                    config.player_name_pos = (x, y - PLAYER_HEIGHT // 2)
                
               
                self.minimap = {
                    'minimap':      minimap,
                    'path':         config.path,
                    'player_name_pos':   config.player_name_pos,
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
                        config.bot.found_monster = False
                        config.bot.monster_dir = None
                        continue

                    # 앞/뒤 영역 계산 (x1,y1,x2,y2)
                    if facing_left and facing_right == False :
                        # 왼쪽이 앞
                        fx1, fx2 = px - front, px + back
                        bx1, bx2 = px - back,  px + front
                    elif facing_right and facing_left == False:
                        # 오른쪽이 앞
                        fx1, fx2 = px - back,  px + front
                        bx1, bx2 = px - front, px + back
                    else:
                        config.bot.found_monster = False
                        return  # 또는 continue

                    fy1, fy2 = py - up, py + down
                    by1, by2 = fy1, fy2

                    # 클램프
                    fx1 = max(0, int(fx1)); fy1 = max(0, int(fy1))
                    fx2 = min(W, int(fx2)); fy2 = min(H, int(fy2))

                    bx1 = max(0, int(bx1)); by1 = max(0, int(by1))
                    bx2 = min(W, int(bx2)); by2 = min(H, int(by2))

                    # 잘못된 영역 방지
                    if fx2 <= fx1 or fy2 <= fy1 or bx2 <= bx1 or by2 <= by1:
                        config.bot.found_monster = False
                        config.bot.monster_dir = None
                        continue

                    # ROI 추출
                    front_roi = self.frame[fy1:fy2, fx1:fx2]
                    back_roi  = self.frame[by1:by2, bx1:bx2]

                        
                    front_gray = cv2.cvtColor(front_roi, cv2.COLOR_BGRA2GRAY) if front_roi.size != 0 else None
                    back_gray  = cv2.cvtColor(back_roi,  cv2.COLOR_BGRA2GRAY)  if back_roi.size  != 0 else None

                    # 탐지 (※ 회전/공격은 하지 않는다!)
                    back_found  = self._has_monster(back_gray,  MONSTER_TEMPLATES, threshold=0.7)
                    front_found = self._has_monster(front_gray, MONSTER_TEMPLATES, threshold=0.7)
                    
                    if front_found and back_found:
                        config.bot.found_monster = True
                        config.bot.monster_dir = 'front'
                        self._attack_immediate('front')
                        # utils.capture_minimap(fx1, fy1, fx2, fy2)
                    elif front_found == False and back_found:
                        config.bot.found_monster = True
                        config.bot.monster_dir = 'back'
                        # 즉시 공격
                        self._attack_immediate('back')
                        # utils.capture_minimap(bx1, by1, bx2, by2)  # 디버그 필요 시만
                    elif front_found and back_found == False :
                        config.bot.found_monster = True
                        config.bot.monster_dir = 'front'
                        self._attack_immediate('front')
                        # utils.capture_minimap(fx1, fy1, fx2, fy2)
                    else:
                        # 공격 키가 눌린 채로 남지 않도록 정리
                        bot = getattr(config, 'bot', None)
                        if bot and bot.shift_down:
                            pyautogui.keyUp(bot.attack_key)
                            bot.shift_down = False
                        config.bot.found_monster = False
                        config.bot.monster_dir = None

                    time.sleep(0.001)

                        

                time.sleep(0.001)
    def _face(self, to_dir: str):
        bot = getattr(config, 'bot', None)
        if not bot:
            return
        bot.face(to_dir)  # <<<<<< 단 한 줄만
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
