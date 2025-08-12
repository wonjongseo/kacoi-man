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

MM_TL_TEMPLATE = cv2.imread('assets/minimap_topLeft.png', 0)
MM_BR_TEMPLATE = cv2.imread('assets/minimap_bottomRight.png', 0)

# 이 (MMT_HEIGHT, MMT_WIDTH) 크기만큼은 최소한 확보해야 템플릿 전체가 포함된다
MMT_HEIGHT = max(MM_TL_TEMPLATE.shape[0], MM_BR_TEMPLATE.shape[0])
MMT_WIDTH = max(MM_TL_TEMPLATE.shape[1], MM_BR_TEMPLATE.shape[1])

PLAYER_TEMPLATE = cv2.imread('assets/me.png', 0)
PT_HEIGHT, PT_WIDTH = PLAYER_TEMPLATE.shape


# PLAYER_NAME_TEMPLATE = cv2.imread('assets/charactor.png', 0)
PLAYER_HEIGHT = 70 # 실제 캐릭터 높이

#
# MONSTERS_FOLDER = 'assets/monsters/pigsBitch'
# MONSTER_TEMPLATES = utils.load_templates(MONSTERS_FOLDER)


class Capture:
    """
    A class that tracks player position and various in-game events. It constantly updates
    the config module with information regarding these events. It also annotates and
    displays the minimap in a pop-up window.
    """

    def __init__(self):
        """Initializes this Capture object's main thread."""

        # 전역 config 모듈에 자신을 등록
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
            'right' : 0,
            'width' : 970, # 1366,
            'height': 700  # 768
        }

        # 상태 플래그
        self.ready = False     # GUI가 최초 정보 수신을 기다릴 때 사용
        self.calibrated = False  # 미니맵 위치 보정이 완료되었는지 여부

        # 백그라운드 스레드 생성
        self.thread = threading.Thread(target=self._main)
        self.thread.daemon = True

        # self.potionThread = threading.Thread(target=self._potionMain)
        # self.potionThread.daemon = True
        
        self.window_resized = False
        threading.Thread(
        target=PotionManager(
            bar_h_margin=2,      # 템플릿이 바 안쪽만 찍혔으면 0~2px 여유
            bar_v_margin=0,
            hp_thresh=0.4,       # 60 % 미만에서 사용
            mp_thresh=0.5
        ).loop,
        daemon=True
    ).start()


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
        while self.window_resized is False:
            windows = gw.getWindowsWithTitle(config.TITLE)
            print(f'windows : {windows}')
            
            if windows:
                win = windows[0]
                win.moveTo(0, 0)
                win.resizeTo(970, 700)
                handle_windows.activate_window(win.title)
                config.TITLE = win.title
                print(f"[INFO] '{win.title}' 창 크기 설정 완료.")
                self.window_resized = True
                time.sleep(0.5)
            else:
                print(f"[ERROR] 창을 찾을 수 없음: '{config.TITLE}'")

        while True:
            self.roop_screen()
    
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
                    if config.player_name_pos is None:
                        continue

                    px, py = config.player_name_pos  # px = X, py = Y

                    # if config.bot.keydown is "left":
                    if config.bot.left_down:
                        x1, x2 = max(0, px - 300), px
                    else:
                        x1, x2 = px, min(self.frame.shape[1], px + 300)
                
                    y1 = max(0, py - 100)
                    y2 = min(self.frame.shape[0], py + 100)

                    x1, x2, y1, y2 = map(int, (x1, x2, y1, y2))

                    attack_area = self.frame[y1:y2, x1:x2]
                    if attack_area.size == 0:
                        continue 
                    gray_area = cv2.cvtColor(attack_area, cv2.COLOR_BGRA2GRAY)
                    
                    for tpl in MONSTER_TEMPLATES:
                        h_img, w_img = gray_area.shape
                        h_tpl, w_tpl = tpl.shape

                        # 템플릿이 더 크면 스킵
                        if h_img < h_tpl or w_img < w_tpl:
                            continue
                        res = cv2.matchTemplate(gray_area, tpl, cv2.TM_CCOEFF_NORMED)
                        if np.any(res >= 0.7):
                            # # ── 몬스터 감지 시 한 번만 실행 ──
                            config.bot.found_monster = True
                            # pyautogui.keyUp('z')
                            # pyautogui.keyDown("shift")
                            utils.capture_minimap(x1, y1 , x2,  y2)
                            break
                    else:
                        config.bot.found_monster = False
                        
                        # pyautogui.keyUp("shift")
                        # pyautogui.keyDown('z')

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
