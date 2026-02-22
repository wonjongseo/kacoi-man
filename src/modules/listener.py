import time
import threading
import winsound
import keyboard as kb
from dataclasses import dataclass
from typing import List
from src.common import config, utils, handle_windows
import math



@dataclass
class _BuffTask:
    key: str
    cooldown: float          # seconds
    next_at: float = 0.0
    last_at: float = 0.0


class Listener:
    def __init__(self):
        config.listener = self

        self.ready = False
        self.enabled = True


        self.thread = threading.Thread(target=self._main, daemon=True)


        self._last_cast_ts = 0.0
        self._alive = threading.Event()
        self._cv = threading.Condition()

        self._buff_tasks: List[_BuffTask] = []
        self._buff_thread = threading.Thread(target=self._buff_loop, daemon=True)
    

    def reload_buffs_from_config(self):
        s = getattr(config, "setting_data", None)
        buffs = getattr(s, "buffs", []) if s else []
        tasks: List[_BuffTask] = []
        now = time.time()
        for b in buffs or []:
            key = (getattr(b, "key", "") or "").strip()
            cd = float(getattr(b, "cooldown_sec", 0) or 0)
            if not key or cd <= 0:
                continue

            tasks.append(_BuffTask(key=key, cooldown=cd, next_at=float('inf')))

        with self._cv:
            self._buff_tasks = tasks
            self._cv.notify_all()
        print(f"[Listener] buffs reloaded: {len(self._buff_tasks)} task(s)")

    def start(self):
        if self.ready:
            return
    
        print('\n[~] Started keyboard listener')
        self._alive.set()

        self.reload_buffs_from_config()

        self.thread.start()
        self._buff_thread.start()
        self.ready = True
    
    def stop(self, timeout=2.0):
        if config.macro_shutdown_evt:
            config.macro_shutdown_evt.set()

        # if self.thread and self.thread.is_alive():
        #     self.thread.join(timeout=2)
            
        self._alive.clear()
        with self._cv:
            self._cv.notify_all()
        if self._buff_thread.is_alive():
            self._buff_thread.join(timeout=timeout)

    def _main(self):
        """Constantly listens for user inputs and updates variables in config accordingly."""
        self.ready = True
        while not (config.macro_shutdown_evt and config.macro_shutdown_evt.is_set()):
            try:
                if self.enabled:
                    if kb.is_pressed('f9'):
                        Listener.toggle_enabled()

                        while kb.is_pressed('f9'):
                            time.sleep(0.05)

                    elif kb.is_pressed('f8'):
                        x, y = config.player_pos_ab

                        try:
                            form = config.gui.edit.form_panel
                            form.var_x.set(x)
                            form.var_y.set(y)
                        except Exception:
                            pass

                        while kb.is_pressed('f8'):
                            time.sleep(0.05)
                    elif kb.is_pressed('f6'):
                        config.no_monster_c_enabled = not getattr(config, "no_monster_c_enabled", False)
                        state = "ON" if config.no_monster_c_enabled else "OFF"
                        print(f"[Listener] no-monster teleport: {state}")
                        winsound.Beep(880 if config.no_monster_c_enabled else 440, 120)
                        while kb.is_pressed('f6'):
                            time.sleep(0.05)

            except Exception as e:
                print(f"[Listener Error] {e}")
            time.sleep(0.01)

    @staticmethod
    def toggle_enabled():
        """Resumes or pauses the current routine. Plays a sound to notify the user."""
        if config.setting_data is None:
            utils.display_message('확인', "게임 셋팅을 적용해주세요.")
            return
        if config.routine is None:
            utils.display_message('확인', "루틴을 적용해주세요.")
            return
        if not getattr(config.routine, "items", None):
            utils.display_message('확인', "루틴 액션이 비어있습니다.")
            return

        config.enabled = not config.enabled
        config.gui.monitor.set_enable()
        if config.enabled:
            handle_windows.activate_window(config.TITLE)
            config.gui.monitor.refresh_routine()

            try:
                if getattr(config, "listener", None):
                    config.listener._prime_buffs_on_enable()
            except Exception as e:
                print(f"[Listener] prime buffs on enable failed: {e}")
            winsound.Beep(784, 333)  # G5
        else:
            winsound.Beep(523, 333)  # C5
            if getattr(config, "bot", None):
                config.bot.release_all_keys()
        time.sleep(0.267)


    # Buff scheduler internals

    def _prime_buffs_on_enable(self):
        now = time.time()
        with self._cv:
            stagger = 0.0
            for t in self._buff_tasks:
                t.next_at = now + 0.2 + stagger
                t.last_at = 0.0
                stagger += 0.1

            self._last_cast_ts = now
            self._cv.notify_all()

    def _buff_loop(self):
        """버프 스케줄링/시전 루프 (shutdown_evt + Condition 기반)."""
        while self._alive.is_set():
            if config.enabled is False:
                time.sleep(0.1)
                continue

            with self._cv:
                if not self._buff_tasks:
                    self._cv.wait(timeout=0.5)
                    continue
                now = time.time()
                finite_tasks = [t for t in self._buff_tasks if math.isfinite(t.next_at)]
                if finite_tasks:
                    due = min(t.next_at for t in finite_tasks)

                    timeout = max(0.0, min(5.0, due - now))
                else:

                    timeout = 0.5
                self._cv.wait(timeout=timeout)

            if not self._alive.is_set():
                break


            if not config.enabled:
                time.sleep(0.2)
                continue

            bot = getattr(config, "bot", None)
            if bot is not None:
                while self._alive.is_set() and time.time() < bot.attack_anim_until:
                    time.sleep(0.02)

            now = time.time()
            since = now - self._last_cast_ts
            if since < 1.0:
                time.sleep(1.0 - since)
                continue

            fired = False
            for t in self._buff_tasks:
                if t.next_at <= time.time():
                    self._fire_buff(t)
                    now2 = time.time()
                    t.last_at = now2
                    t.next_at = now2 + t.cooldown
                    self._last_cast_ts = now2
                    fired = True
                    break
            if not fired:

                time.sleep(0.05)

    def _fire_buff(self, task: _BuffTask):
        """실제 키 입력. keyboard 실패 시 pyautogui로 백업."""
        try:
            kb.send(task.key)
        except Exception:
            try:
                import pyautogui
                parts = [p.strip() for p in task.key.split("+")]
                pyautogui.hotkey(*parts)
            except Exception as e:
                print(f"[Listener] buff send failed ({task.key}): {e}")
        print(f"[Listener] buff -> {task.key}")
