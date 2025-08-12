
import time
import threading
import winsound
import keyboard as kb
from src.common import config, utils

import time
from src.modules.bot import Bot
from src.modules.capture import Capture
from src.modules.notifier import Notifier



class Listener: 
    def __init__(self):
        config.listener = self

        self.ready = False
        self.enabled = True

        self.thread = threading.Thread(target=self._main)
        self.thread.daemon = True
        
    def start(self):
        """
        Starts listening to user inputs.
        :return:    None
        """
        print('\n[~] Started keyboard listener')
        self.thread.start()

    def _main(self):
        """
        Constantly listens for user inputs and updates variables in config accordingly.
        :return:    None
        """

        self.ready = True
        while True:
            try:
                if self.enabled:
                    if kb.is_pressed('f9'):
                        Listener.toggle_enabled()
                    elif kb.is_pressed('f8'):
                        x, y = config.player_pos_ab
                        config.gui.edit.form_panel.var_x.set(x)
                        config.gui.edit.form_panel.var_y.set(y)
                    elif kb.is_pressed('f7'):
                        print(f'config.setting_data: {config.setting_data}')
                        bot = Bot()
                        capture = Capture()
                        notifier = Notifier()

                        capture.start()
                        print("Aa")
                        while not capture.ready:
                            time.sleep(0.01)
                        bot.start()
                        while not bot.ready:
                            time.sleep(0.01)
                       

                        notifier.start()
                        while not notifier.ready:
                            time.sleep(0.01)
                        
                    # if kb.is_pressed("left"):
                    #    config.bot.keydown = 'left'
                    # elif kb.is_pressed("right"):
                    #    config.bot.keydown = 'right'
                    # if kb.is_pressed("shift"):
                    #     print('shift down')
                    
            except Exception as e:
                print(f"[Listener Error] {e}")
            time.sleep(0.01)
    @staticmethod    
    def toggle_enabled():
        """Resumes or pauses the current routine. Plays a sound to notify the user."""

        config.enabled = not config.enabled
        if config.enabled:
            winsound.Beep(784, 333)     # G5
        else:
            winsound.Beep(523, 333)     # C5
        time.sleep(0.267)