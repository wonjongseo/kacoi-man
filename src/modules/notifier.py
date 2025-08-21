

from src.common import config, utils
import time
import os
import cv2
import pygame
import threading
import numpy as np
import keyboard as kb
from src.routine.components import Point

# Other players' symbols on the minimap
OTHER_RANGES = (
((0, 245, 215), (10, 255, 255)),
)

PLAYER_RANGES = (
    ((60, 100, 100), (55, 92, 85)),
)

# other_filtered = utils.filter_color(cv2.imread('assets/other.png'), OTHER_RANGES)
# OTHER_TEMPLATE = cv2.cvtColor(other_filtered, cv2.COLOR_BGR2GRAY)

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
        self.thread = threading.Thread(target=self._main)
        self.thread.daemon = True
        
    
    def start(self):
        """Starts this Notifier's thread."""

        print('\n[~] Started notifier')
        self.thread.start()
    
    def stop(self):
        if config.macro_shutdown_evt:
            config.macro_shutdown_evt.set()
        # 필요시 조인
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
                if np.count_nonzero(gray < 15) / height / width > self.room_change_threshold:
                    self._alert('siren')
                    
                
                filtered = utils.filter_color(minimap, OTHER_RANGES)
                others = len(utils.multi_match(filtered, OTHER_TEMPLATE, threshold=0.5))
                
                if others != prev_others:
                    if others > prev_others:
                        config.appear_other = True
                        self._ping('ding')
                    prev_others = others
                elif others == 0:
                    config.appear_other = False

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