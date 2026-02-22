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

WINDOWED_OFFSET_TOP = 0 #36 # 李?紐⑤뱶??????댄? 諛??믪씠 蹂댁젙
WINDOWED_OFFSET_LEFT = 0 #10 # 李?紐⑤뱶????醫뚯륫 蹂댁젙

PLAYER_INFO_TOP = 620

MM_TL_TEMPLATE = cv2.imread(utils.resource_path('assets/minimap_topLeft.png'), 0)
MM_BR_TEMPLATE = cv2.imread(utils.resource_path('assets/minimap_bottomRight.png'), 0)

# ??(MMT_HEIGHT, MMT_WIDTH) ?ш린留뚰겮? 理쒖냼???뺣낫?댁빞 ?쒗뵆由??꾩껜媛 ?ы븿?쒕떎
if MM_TL_TEMPLATE is not None and MM_BR_TEMPLATE is not None:
    MMT_HEIGHT = max(MM_TL_TEMPLATE.shape[0], MM_BR_TEMPLATE.shape[0])
    MMT_WIDTH = max(MM_TL_TEMPLATE.shape[1], MM_BR_TEMPLATE.shape[1])
else:
    MMT_HEIGHT, MMT_WIDTH = 1, 1

PLAYER_TEMPLATE = cv2.imread(utils.resource_path('assets/me.png'), 0)
if PLAYER_TEMPLATE is not None:
    PT_HEIGHT, PT_WIDTH = PLAYER_TEMPLATE.shape
else:
    PT_HEIGHT, PT_WIDTH = 1, 1


# PLAYER_NAME_TEMPLATE = cv2.imread('assets/charactor.png', 0)
PLAYER_HEIGHT = 70 # ?ㅼ젣 罹먮┃???믪씠

#
# MONSTERS_FOLDER = 'assets/monsters/pigsBitch'
# MONSTER_TEMPLATES = utils.load_templates(MONSTERS_FOLDER)


class Capture:
    def _ensure_templates(self):
        """?쒗뵆由우쓣 1??濡쒕뱶?섍퀬 ?뚯깮 ?ш린 怨꾩궛 (PyInstaller ???."""
        if self._mm_tl_tmpl is None:
            self._mm_tl_tmpl = cv2.imread(utils.resource_path('assets/minimap_topLeft.png'), 0)
        if self._mm_br_tmpl is None:
            self._mm_br_tmpl = cv2.imread(utils.resource_path('assets/minimap_bottomRight.png'), 0)
        if self._player_tmpl is None:
            self._player_tmpl = cv2.imread(utils.resource_path('assets/me.png'), 0)
        if self._mm_tl_tmpl is None or self._mm_br_tmpl is None or self._player_tmpl is None:
            raise FileNotFoundError("Required minimap/player templates are missing.")

        # ?뚯깮 ?ш린
        th1, tw1 = self._mm_tl_tmpl.shape[:2]
        th2, tw2 = self._mm_br_tmpl.shape[:2]
        self._MMT_HEIGHT = max(th1, th2)
        self._MMT_WIDTH = max(tw1, tw2)

        self._PT_HEIGHT, self._PT_WIDTH = self._player_tmpl.shape[:2]


    def __init__(self):
        """Initializes this Capture object's main thread."""

        config.capture = self

        # ?꾨젅?꾧낵 誘몃땲留?愿???띿꽦 珥덇린??
        self.frame = None                 # ?꾩껜 ?붾㈃ 罹≪쿂 ?대?吏
        self.minimap = {}                 # GUI???꾨떖??誘몃땲留??뺣낫
        self.minimap_ratio = 1            # 誘몃땲留?媛濡??몃줈 鍮꾩쑉
        self.minimap_sample = None        # 誘몃땲留?罹섎━釉뚮젅?댁뀡 ?섑뵆

        # mss ?ㅽ겕由곗꺑 媛앹껜 珥덇린???먮━ ?쒖떆
        self.sct = None
        self._mm_tl_tmpl = MM_TL_TEMPLATE
        self._mm_br_tmpl = MM_BR_TEMPLATE
        self._player_tmpl = PLAYER_TEMPLATE
        self._MMT_HEIGHT = MMT_HEIGHT
        self._MMT_WIDTH = MMT_WIDTH
        self._PT_HEIGHT = PT_HEIGHT
        self._PT_WIDTH = PT_WIDTH
        self._ensure_templates()

        # 罹≪쿂 ????덈룄???곸뿭 (left, top, width, height)
        self.window = { 
            'left' : 0,
            'top' : 0,
            'width' : config.SCREEN_WIDTH, # 1366,
            'height': config.SCREEN_HEIGHT  # 768
        }

        self.ready = False     # GUI媛 理쒖큹 ?뺣낫 ?섏떊??湲곕떎由????ъ슜
        self.calibrated = False  # 誘몃땲留??꾩튂 蹂댁젙???꾨즺?섏뿀?붿? ?щ?

        # 諛깃렇?쇱슫???ㅻ젅???앹꽦
        self.thread = threading.Thread(target=self._main)
        self.thread.daemon = True

        # self.potionThread = threading.Thread(target=self._potionMain)
        # self.potionThread.daemon = True
        
        self.last_attack_t = 0.0
        self.attack_interval = 0.14   # 怨듦꺽 理쒖냼 媛꾧꺽(珥? - ?꾩슂??0.10~0.20 ?쒕떇
        config.attack_in_capture = True  # 罹≪쿂 ?ㅻ젅?쒓? 怨듦꺽???대떦


        self.window_resized = False
        threading.Thread(target=PotionManager().loop,daemon=True).start()

    def _attack_immediate(self, dir_hint: str):
        bot = getattr(config, 'bot', None)
        if not bot or not config.enabled:
            return
        if bot.is_climbing or bot.up_down:   # ?щ떎由?理쒖슦??
            return

        now = time.time()
        if now - self.last_attack_t < self.attack_interval:
            return

        # 諛⑺뼢 蹂댁젙
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

        # ??怨듦꺽(???대?)
        bot.tap_attack(dur=0.01)
        self.last_attack_t = now
        bot.mark_attack()  # ??怨듦꺽 紐⑥뀡 吏꾪뻾 以??쒖떆
    def start(self): 
        print('\n[~] Started video capture')
        self.thread.start()
    

    def _main(self):
        """Constantly monitors the player's position and in-game events."""
        """
            紐⑹쟻: Windows ?꾩슜 ?ㅽ겕由곗꺑 諛⑹떇?먯꽌 遺덊븘?뷀븳 ?щ챸(?щ챸李? ?뺣낫瑜?諛곗젣?섍퀬 鍮좊Ⅴ寃??붾㈃??罹≪쿂?섍린 ?꾪빐 ?ㅼ젙
            ?④낵: GDI ?몄텧 ??CAPTUREBLT ?뚮옒洹몃? ?붿쑝濡쒖뜥, ?덉빻? 李??꾩뿉 ?ㅻⅨ 李쎌씠 寃뱀퀜 ?덈뜑?쇰룄 鍮꾪듃留?BLT) 蹂묓빀 怨쇱젙???앸왂
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
                print(f"[INFO] '{win.title}' 李??ш린 ?ㅼ젙 ?꾨즺.")
                self.window_resized = True
                time.sleep(0.5)
            else:
                print(f"[ERROR] 李쎌쓣 李얠쓣 ???놁쓬: '{config.TITLE}'")
        while not (config.macro_shutdown_evt and config.macro_shutdown_evt.is_set()):
            self.roop_screen()
            time.sleep(0.001)
    def stop(self):
        if config.macro_shutdown_evt:
            config.macro_shutdown_evt.set()
        # ?꾩슂??議곗씤
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
        self.window['width'] = max(rect[2] - rect[0], self._MMT_WIDTH)
        self.window['height'] = max(rect[3] - rect[1], self._MMT_HEIGHT)
        
        with mss.mss() as self.sct:
            self.frame = self.screenshot()
        if self.frame is None:
            return

        tl, _ = utils.single_match(self.frame, self._mm_tl_tmpl)
        
        _, br = utils.single_match(self.frame, self._mm_br_tmpl)

        mm_tl = (
            tl[0] + MINIMAP_BOTTOM_BORDER,
            tl[1] + MINIMAP_TOP_BORDER
        )
    
        mm_br = (
            max(mm_tl[0] + self._PT_WIDTH, br[0] - MINIMAP_BOTTOM_BORDER), # ???
            max(mm_tl[1] + self._PT_HEIGHT, br[1] - MINIMAP_BOTTOM_BORDER)
        )
        
        self.minimap_ratio = (mm_br[0] - mm_tl[0]) / (mm_br[1] - mm_tl[1]) # 怨꾩궛???댄빐 ?덈맂???
        self.minimap_sample = self.frame[mm_tl[1]:mm_br[1], mm_tl[0]:mm_br[0]] # 怨꾩궛???댄빐 ?덈맂???
        self.calibrated = True

        MONSTERS_FOLDER = config.setting_data.monster_dir
        MONSTER_TEMPLATES = utils.load_templates(MONSTERS_FOLDER) or []
        player_name_template = cv2.imread(config.setting_data.templates.character.name, 0)

        with mss.mss() as self.sct:
            while not (config.macro_shutdown_evt and config.macro_shutdown_evt.is_set()):
                if not self.calibrated:
                    break
                self.frame = self.screenshot()
                if self.frame is None:
                    continue
                else:
                    self.frame = self.frame[:PLAYER_INFO_TOP, ::] # ?섎떒??罹먮┃???대쫫 / ?덈꺼 ?꾩튂 ?쒓굅

                minimap = self.frame[ mm_tl[1]:mm_br[1], mm_tl[0]:mm_br[0] ]
                player = utils.multi_match(minimap, self._player_tmpl, threshold=0.8)
                

                config.margin_tl = self.window['left'] + mm_tl[0]
                config.margin_tr = self.window['top']  + mm_tl[1] 


                if player:
                    config.player_pos_ab = (config.margin_tl + player[0][0], config.margin_tr + player[0][1])

                frame_h, frame_w = self.frame.shape[:2]
                cropped_frame = self.frame[0:frame_h+100, :]
                player_name = None
                if player_name_template is not None:
                    player_name = utils.single_match(cropped_frame, player_name_template)

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
                    
                    
                    H, W = self.frame.shape[:2]

                    facing_left  = (config.bot.left_down  and not config.bot.right_down)
                    facing_right = (config.bot.right_down and not config.bot.left_down)

                    if not (facing_left or facing_right):
                        config.bot.found_monster = False
                        config.bot.monster_dir = None
                        continue

                    # ?????곸뿭 怨꾩궛 (x1,y1,x2,y2)
                    if facing_left and facing_right == False :
                        # ?쇱そ????
                        fx1, fx2 = px - front, px + back
                        bx1, bx2 = px - back,  px + front
                    elif facing_right and facing_left == False:
                        # ?ㅻⅨ履쎌씠 ??
                        fx1, fx2 = px - back,  px + front
                        bx1, bx2 = px - front, px + back
                    else:
                        config.bot.found_monster = False
                        return  # ?먮뒗 continue

                    fy1, fy2 = py - up, py + down
                    by1, by2 = fy1, fy2

                    # ?대옩??
                    fx1 = max(0, int(fx1)); fy1 = max(0, int(fy1))
                    fx2 = min(W, int(fx2)); fy2 = min(H, int(fy2))

                    bx1 = max(0, int(bx1)); by1 = max(0, int(by1))
                    bx2 = min(W, int(bx2)); by2 = min(H, int(by2))

                    # ?섎せ???곸뿭 諛⑹?
                    if fx2 <= fx1 or fy2 <= fy1 or bx2 <= bx1 or by2 <= by1:
                        config.bot.found_monster = False
                        config.bot.monster_dir = None
                        continue

                    # ROI 異붿텧
                    front_roi = self.frame[fy1:fy2, fx1:fx2]
                    back_roi  = self.frame[by1:by2, bx1:bx2]

                        
                    front_gray = cv2.cvtColor(front_roi, cv2.COLOR_BGRA2GRAY) if front_roi.size != 0 else None
                    back_gray  = cv2.cvtColor(back_roi,  cv2.COLOR_BGRA2GRAY)  if back_roi.size  != 0 else None

                    # ?먯? (???뚯쟾/怨듦꺽? ?섏? ?딅뒗??)
                    back_found  = self._has_monster(back_gray,  MONSTER_TEMPLATES, threshold=0.7)
                    front_found = self._has_monster(front_gray, MONSTER_TEMPLATES, threshold=0.7)
                    
                    if front_found and back_found:
                        config.bot.found_monster = True
                        config.bot.monster_dir = 'front'
                        self._attack_immediate('front')
                        utils.capture_minimap(fx1, fy1, fx2, fy2)
                    elif front_found == False and back_found:
                        config.bot.found_monster = True
                        config.bot.monster_dir = 'back'
                        # 利됱떆 怨듦꺽
                        self._attack_immediate('back')
                        # utils.capture_minimap(bx1, by1, bx2, by2)  # ?붾쾭洹??꾩슂 ?쒕쭔
                    elif front_found and back_found == False :
                        config.bot.found_monster = True
                        config.bot.monster_dir = 'front'
                        self._attack_immediate('front')
                        # utils.capture_minimap(fx1, fy1, fx2, fy2)
                    else:
                        # 怨듦꺽 ?ㅺ? ?뚮┛ 梨꾨줈 ?⑥? ?딅룄濡??뺣━
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
        bot.face(to_dir)  # <<<<<< ????以꾨쭔
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
