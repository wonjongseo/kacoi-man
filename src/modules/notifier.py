

from src.common import config, utils, handle_windows, default_value as dv
import time
import os
import cv2
import pygame
import threading
import numpy as np
import keyboard as kb
import pyautogui
import mss

# Other players' symbols on the minimap
OTHER_RANGES = (
((0, 245, 215), (10, 255, 255)),
)

PLAYER_RANGES = (
    ((60, 100, 100), (55, 92, 85)),
)


def get_alert_path(name):
    return os.path.join(Notifier.ALERTS_DIR, f'{name}.mp3')

class Notifier:
    ALERTS_DIR = os.path.join('assets', 'alerts')

    def __init__(self):
        """Initializes this Notifier object's main thread."""
        config.notifier = self
        pygame.mixer.init()
        self.mixer = pygame.mixer.music

        self.ready = False

        self.other_detected = True
        self.room_change_threshold = 0.9

        self.cnt_found_other = 0 
        self._other_action_due_at = None
        self._vildge_paper_template = cv2.imread(
            utils.resource_path('assets/vildge_paper.png'),
            cv2.IMREAD_GRAYSCALE,
        )
        self.thread = threading.Thread(target=self._main)
        self.thread.daemon = True
        
    
    def start(self):
        """Starts this Notifier's thread."""

        print('\n[~] Started notifier')
        self.thread.start()
    
    def stop(self):
        if config.macro_shutdown_evt:
            config.macro_shutdown_evt.set()

        # if self.thread and self.thread.is_alive():
        #     self.thread.join(timeout=2)

    def _main(self):    
        
        selected_other = config.setting_data.templates.minimap.other
        
        if selected_other is None or selected_other == "":
            other_filtered = utils.filter_color(cv2.imread(utils.resource_path('assets/other.png')), OTHER_RANGES)
        else:
            other_filtered = utils.filter_color(cv2.imread(selected_other), OTHER_RANGES)
        OTHER_TEMPLATE = cv2.cvtColor(other_filtered, cv2.COLOR_BGR2GRAY)

        # seledted_revive_msg = config.setting_data.templates.misc.revive_message

        # if seledted_revive_msg is None or seledted_revive_msg == "":
        #     REVIVE_MSG_TEMPLATE =  cv2.imread('assets/revived_msg.png', 0)
        # else:
        #     REVIVE_MSG_TEMPLATE =  cv2.imread(seledted_revive_msg, 0)
        

        self.ready = True
        prev_others = 0

        while not (config.macro_shutdown_evt and config.macro_shutdown_evt.is_set()):
            if config.enabled:
                frame = config.capture.frame
                height, width, _ = frame.shape
                minimap = config.capture.minimap['minimap']

                # Check for unexpected black screen
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                suppress_until = float(getattr(config, "black_screen_suppress_until", 0.0) or 0.0)
                if time.time() < suppress_until:
                    pass
                elif np.count_nonzero(gray < 15) / height / width > self.room_change_threshold:
                    self._alert('siren')
                    
                
                filtered = utils.filter_color(minimap, OTHER_RANGES)
                others = len(utils.multi_match(filtered, OTHER_TEMPLATE, threshold=0.5))
                
                now = time.time()
                if others > 0 and prev_others == 0:
                    config.appear_other = True
                    self._ping('ding')
                    self._other_action_due_at = now + dv.OTHER_APPEAR_ACTION_DELAY_SEC

                if others == 0:
                    config.appear_other = False
                    self._other_action_due_at = None

                if others > 0 and self._other_action_due_at is not None and now >= self._other_action_due_at:
                    self._press_interact_key()
                    self._other_action_due_at = None

                prev_others = others

                # is_dead = cv2.matchTemplate(frame, REVIVE_MSG_TEMPLATE, cv2.TM_CCOEFF_NORMED) 


                # is_dead = utils.single_match(frame, REVIVE_MSG_TEMPLATE)
                # print(f'is_dead : {is_dead}')
                
            time.sleep(3)

    def _alert(self, name, volume=0.75):
        """
        Plays an alert to notify user of a dangerous event. Stops the alert
        once the key bound to 'Start/stop' is pressed.
        """
        config.bot.release_all_keys()
        config.enabled = False
        config.listener.enabled = False
        self.mixer.load(get_alert_path(name))
        self.mixer.set_volume(volume)
        self.mixer.play(-1)
        
        while not kb.is_pressed("f9"):
            time.sleep(0.1)
        self.mixer.stop()
        time.sleep(2)
        config.listener.enabled = True

    def _ping(self, name, volume=0.5):
        print("ping")
        """A quick notification for non-dangerous events."""

        self.mixer.load(get_alert_path(name))
        self.mixer.set_volume(volume)
        self.mixer.play()

    def _press_interact_key(self):
        try:
            handle_windows.activate_window(config.TITLE)
            time.sleep(0.05)
        except Exception:
            pass

        sent = False
        try:
            pyautogui.keyDown('i')
            time.sleep(0.03)
            pyautogui.keyUp('i')
            sent = True
        except Exception as e:
            print(f"[Notifier] pyautogui i down/up failed: {e}")

        if not sent:
            try:
                pyautogui.press('i')
                sent = True
            except Exception as e:
                print(f"[Notifier] pyautogui.press('i') failed: {e}")

        if not sent:
            try:
                kb.send('i')
                sent = True
            except Exception as e:
                print(f"[Notifier] keyboard.send('i') failed: {e}")

        if not sent:
            print("[Notifier] failed to send interact key 'i'")
            return

        time.sleep(1.0)
        self._click_vildge_paper_in_window()

    def _click_vildge_paper_in_window(self, threshold=0.72):
        template = self._vildge_paper_template
        if template is None:
            print("[Notifier] assets/vildge_paper.png not found")
            return False

        cap = getattr(config, "capture", None)
        if not cap or not getattr(cap, "window", None):
            return False

        win = cap.window
        monitor = {
            "left": int(win.get("left", 0)),
            "top": int(win.get("top", 0)),
            "width": int(win.get("width", 0)),
            "height": int(win.get("height", 0)),
        }
        if monitor["width"] <= 0 or monitor["height"] <= 0:
            return False

        with mss.mss() as sct:
            frame = np.array(sct.grab(monitor))[:, :, :3]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        th, tw = template.shape[:2]
        fh, fw = gray.shape[:2]
        if th > fh or tw > fw:
            return False

        result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val < threshold:
            print(f"[Notifier] vildge_paper not found (score={max_val:.2f})")
            return False

        click_x = monitor["left"] + max_loc[0] + (tw // 2)
        click_y = monitor["top"] + max_loc[1] + (th // 2)
        # Send an explicit double-click with a fixed interval for game input reliability.
        pyautogui.click(click_x, click_y, clicks=2, interval=0.12, button='left')
        print(f"[Notifier] double-clicked vildge_paper at ({click_x}, {click_y}), interval=0.12s")
        return True
