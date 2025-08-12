"""The central program that ties all the modules together."""

import time
from src.modules.bot import Bot, RoutePatrol
from src.modules.gui import GUI
from src.modules.listener import Listener
from src.datas import setting_data as sd
from src.common import config
from src.datas.routine_data import list_from_jsonable  # 너가 만든 액션 dataclass 유틸 (없으면 패스)


import os
import sys
import json


def get_app_dir():
    if getattr(sys, 'frozen', False):
        # PyInstaller로 빌드된 실행파일
        return os.path.dirname(sys.executable)
    else:
        # 일반 파이썬 실행
        return os.path.dirname(os.path.abspath(__file__))
    
def load_json_file(path):
    """JSON 파일을 로드하고 로그 출력"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"[WARN] {os.path.basename(path)} 파일이 없습니다.")
    return None

def init_settings():
    """앱 시작 시 game_setting.json, default_routine.json 로드"""
    app_dir = get_app_dir()

    game_setting_path = os.path.join(app_dir, 'game_setting.json')
    default_routine_path = os.path.join(app_dir, 'default_routine.json')

    game_setting_data = load_json_file(game_setting_path)
    default_routine_data = load_json_file(default_routine_path)

    return game_setting_data, default_routine_data

game_setting, default_routine = init_settings()



gui = GUI()

if game_setting:
    cfg = sd.SettingsConfig.from_dict(game_setting)
    config.setting_data = cfg
    gui.game_setting.set_config(cfg)
    
    if hasattr(gui, "monitor"):
        gui.monitor.refresh_labels()
        gui.monitor.refresh_routine()

    if hasattr(gui, "game_setting"):
        gui.game_setting.start_bot()

if default_routine:
    try:
        items = list_from_jsonable(default_routine)  
    except Exception:
        items = default_routine                      
    config.routine = RoutePatrol(items)   
    gui.edit.list_panel.set_data(items)
    if items:
        gui.edit._load_to_form(items[0])
    if hasattr(gui, "monitor"):
        gui.monitor.refresh_labels()
        gui.monitor.refresh_routine()

gui.start()




