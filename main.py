"""The central program that ties all the modules together."""

import os
import sys
import json
import time
from typing import Optional, Tuple

from src.modules.bot import Bot, RoutePatrol
from src.modules.gui import GUI
from src.modules.listener import Listener
from src.datas import setting_data as sd
from src.common import config, utils
from src.datas.routine_data import list_from_jsonable  # 너가 만든 액션 dataclass 유틸 (없으면 패스)


# -----------------------------
# 경로 유틸
# -----------------------------
def get_app_dir() -> str:
    """PyInstaller(exe) / 일반 파이썬 실행 모두에서 실행 파일(.exe/.py)과 같은 폴더 경로를 반환."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def read_setup_first_two_lines(filename: str = "setup.txt") -> Tuple[Optional[str], Optional[str]]:
    """
    같은 폴더의 setup.txt에서 1, 2번째 줄을 읽어 반환.
    파일이 없거나 줄이 비어있으면 해당 항목은 None.
    인코딩은 utf-8-sig → cp932 → utf-8 순으로 시도.
    """
    app_dir = get_app_dir()
    path = os.path.join(app_dir, filename)
    if not os.path.exists(path):
        # setup.txt 없으면 둘 다 None → 그냥 넘어감
        print(f"[INFO] {filename} 파일이 없어 로드를 건너뜁니다.")
        return None, None

    lines = None
    for enc in ("utf-8-sig", "cp932", "utf-8"):
        try:
            with open(path, "r", encoding=enc) as f:
                lines = [line.rstrip("\r\n") for line in f]
            break
        except UnicodeDecodeError:
            continue
    if lines is None:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = [line.rstrip("\r\n") for line in f]

    line1 = lines[0].strip() if len(lines) >= 1 and lines[0].strip() else None
    line2 = lines[1].strip() if len(lines) >= 2 and lines[1].strip() else None
    return line1, line2

def load_json_file(path: str):
    """JSON 파일을 로드하고 로그 출력."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[WARN] {os.path.basename(path)} 파일이 없습니다.")
    except json.JSONDecodeError as e:
        print(f"[ERROR] {os.path.basename(path)} JSON 파싱 실패: {e}")
    return None


def _resolve_path_if_any(app_dir: str, candidate: Optional[str]) -> Optional[str]:
    """
    candidate가 주어지면:
      - 절대경로면 그대로 사용
      - 상대경로면 app_dir 기준으로 합침
    candidate가 None/빈값이면 None 반환 (기본 파일명 절대 사용하지 않음)
    """
    if not candidate:
        return None
    candidate = os.path.expanduser(candidate)
    return candidate if os.path.isabs(candidate) else os.path.join(app_dir, candidate)


def init_settings():
    """
    앱 시작 시 setup.txt(1,2행)만 사용하여 경로 결정.
    - setup.txt가 없으면 둘 다 None
    - 기본 파일명(game_setting.json / default_routine.json)은 절대 사용하지 않음(존재해도 무시)
    """
    app_dir = get_app_dir()
    line1, line2 = read_setup_first_two_lines()

    game_setting_path = _resolve_path_if_any(app_dir, line1)  # 1행
    default_routine_path = _resolve_path_if_any(app_dir, line2)  # 2행

    print(f"[INFO] game_setting 경로  : {game_setting_path if game_setting_path else '(미지정)'}")
    print(f"[INFO] default_routine 경로: {default_routine_path if default_routine_path else '(미지정)'}")

    game_setting_data = load_json_file(game_setting_path) if game_setting_path else None
    default_routine_data = load_json_file(default_routine_path) if default_routine_path else None
    return game_setting_data, default_routine_data


# -----------------------------
# 앱 로직
# -----------------------------
game_setting, default_routine = init_settings()

gui = GUI()

if game_setting:
    try :
        cfg = sd.SettingsConfig.from_dict(game_setting)
        config.setting_data = cfg
        gui.game_setting.set_config(cfg)

        if hasattr(gui, "monitor"):
            gui.monitor.refresh_labels()
            gui.monitor.refresh_routine()

        if hasattr(gui, "game_setting"):
            gui.game_setting.start_bot()
    except Exception as e:
        utils.display_message("불러오기 실패", "게임 설정 형식의 파일이 아니여서 불러오기에 실패했습니다.")
            

if default_routine:
    try:
        items = list_from_jsonable(default_routine)
    except Exception:
        items = default_routine
    try : 
        config.routine = RoutePatrol(items)
        gui.edit.list_panel.set_data(items)
        if items:
            gui.edit._load_to_form(items[0])
        if hasattr(gui, "monitor"):
            gui.monitor.refresh_labels()
            gui.monitor.refresh_routine()
    except Exception as e:
        utils.display_message("불러오기 실패", "루틴 형식의 파일이 아니여서 불러오기에 실패했습니다.")

gui.start()


# fpyinstaller main.py --onefile --noconsole  --add-data "assets;assets"