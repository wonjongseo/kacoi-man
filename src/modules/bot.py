import threading
import time
from src.constant import route_ptrol
import pyautogui
from src.common import config, utils


class RoutePatrol:
    
    def __init__(self, waypoints):
        self.waypoints = waypoints
        self.index = 0

    def current_wp(self):
        return self.waypoints[self.index]

    def advance(self):
        self.index = (self.index + 1) % len(self.waypoints)


class Bot:
    def __init__(self):
        config.bot = self;

        self.ready = False
        self.thread = threading.Thread(target=self._main)
        self.thread.daemon = True
        self.found_monster = False
        self.keydown = ''

        self.route = RoutePatrol(route_ptrol)

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
            if config.enabled is False:
                time.sleep(0.001)
                continue

            if self.found_monster :
                print("몬스터 감지")
                pyautogui.keyDown("shift")
                config.attack_count += 1
                
                if config.attack_count > 3 :
                    print("attack_count > 3")
            else:
                pyautogui.keyUp("shift")
                config.attack_count = 0

                wp = self.route.current_wp()

                target_x, target_y, act = wp["x"], wp["y"], wp["action"]
                
                if config.capture.minimap is None:
                    continue
                
                # target_x, target_y = utils.convert_to_relative((target_x, target_y), config.capture.minimap['minimap'])
                # cur_x, cur_y = utils.convert_to_relative(config.player_pos_ab,config.capture.minimap['minimap'])
                # print(f'cur_x, cur_y : {cur_x}, {cur_y}')
                # print(f'target_x, target_y : {target_x}, {target_y}')
                print(f'config.player_pos_ab : {config.player_pos_ab}')
                
                if abs(config.player_pos_ab[0] - target_x) < 4 and config.player_pos_ab[1] == target_y:
                    pyautogui.press("alt")
                

                
        