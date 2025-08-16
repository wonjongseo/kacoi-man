"""The central program that ties all the modules together."""

import os
import sys
import json
import time
from typing import Optional

from src.modules.bot import Bot, RoutePatrol
from src.modules.gui import GUI
from src.modules.listener import Listener
from src.datas import setting_data as sd
from src.common import config
from src.datas.routine_data import list_from_jsonable  # 너가 만든 액션 dataclass 유틸 (없으면 패스)


# -----------------------------
# 경로 유틸
# -----------------------------
def get_app_dir() -> str:
    """PyInstaller(exe) / 일반 파이썬 실행 모두에서 실행 파일(.exe/.py)과 같은 폴더 경로를 반환."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def read_setup_first_two_lines(filename: str = "setup.txt") -> tuple[Optional[str], Optional[str]]:
    """
    같은 폴더의 setup.txt에서 1, 2번째 줄을 읽어 반환.
    파일이 없거나 줄이 비어있으면 해당 항목은 None.
    인코딩은 utf-8-sig → cp932 → utf-8 순으로 시도.
    """
    app_dir = get_app_dir()
    path = os.path.join(app_dir, filename)
    if not os.path.exists(path):
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


def _resolve_path(app_dir: str, candidate: Optional[str], default_name: str) -> str:
    """
    candidate가 주어지면:
      - 절대경로면 그대로 사용
      - 상대경로면 app_dir 기준으로 합침
    None/빈값이면 default_name을 app_dir 기준으로 사용
    """
    if candidate:
        candidate = os.path.expanduser(candidate)
        return candidate if os.path.isabs(candidate) else os.path.join(app_dir, candidate)
    return os.path.join(app_dir, default_name)


def init_settings():
    """앱 시작 시 setup.txt(1,2행) → 경로 결정 → game_setting.json, default_routine.json 로드"""
    app_dir = get_app_dir()
    line1, line2 = read_setup_first_two_lines()

    game_setting_path = _resolve_path(app_dir, line1, "game_setting.json")
    default_routine_path = _resolve_path(app_dir, line2, "default_routine.json")

    print(f"[INFO] game_setting 경로  : {game_setting_path}")
    print(f"[INFO] default_routine 경로: {default_routine_path}")

    game_setting_data = load_json_file(game_setting_path)
    default_routine_data = load_json_file(default_routine_path)
    return game_setting_data, default_routine_data


# -----------------------------
# 앱 로직
# -----------------------------
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
