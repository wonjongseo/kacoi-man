import threading
import time

import pyautogui
from src.common import config, utils


class Bot:
    def __init__(self):
        config.bot = self;

        self.ready = False
        self.thread = threading.Thread(target=self._main)
        self.thread.daemon = True
        self.found_monster = False
        self.keydown = ''

    def start(self):
        """
        Starts this Bot object's thread.
        :return:    None
        """

        print('\n[~] Started main bot loop')
        self.thread.start()

    def _main(self):
        self.ready = True
        while True:
            if config.enabled:
                if self.found_monster :
                    print("몬스터 감지")
                    pyautogui.keyDown("shift")
                else:
                    pyautogui.keyUp("shift")
            else:
                time.sleep(0.001)