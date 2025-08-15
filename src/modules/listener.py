import time
import threading
import winsound
import keyboard as kb
from dataclasses import dataclass
from typing import List
from src.common import config, utils, handle_windows
from src.modules.bot import Bot
from src.modules.capture import Capture
from src.modules.notifier import Notifier

# ─────────────────────────────
# Buff 스케줄용 데이터 구조
# ─────────────────────────────
@dataclass
class _BuffTask:
    key: str
    cooldown: float          # seconds
    next_at: float = 0.0     # 다음 실행 epoch
    last_at: float = 0.0     # 마지막 실행 epoch


class Listener:
    def __init__(self):
        config.listener = self

        self.ready = False
        self.enabled = True  # (키 리스너 활성화 의미; 봇 on/off는 config.enabled)

        # ── 키 리스너 스레드 ──
        self.thread = threading.Thread(target=self._main, daemon=True)

        # ── 버프 스케줄러 ──
        self._last_cast_ts = 0.0  # ← 마지막 버프 발사 시각 기록 (전역 간격용)
        self._alive = threading.Event()
        self._cv = threading.Condition()
        self._buff_tasks: List[_BuffTask] = []
        self._buff_thread = threading.Thread(target=self._buff_loop, daemon=True)

    # 외부에서 Settings 적용 후 호출하면 최신 버프들 반영됨
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
            # 처음엔 약간 지연(0.5s) 후 시전; enable 시점에 다시 prime 됨.
            tasks.append(_BuffTask(key=key, cooldown=cd, next_at=now + 0.5))

        with self._cv:
            self._buff_tasks = tasks
            self._cv.notify_all()
        print(f"[Listener] buffs reloaded: {len(self._buff_tasks)} task(s)")

    def start(self):
        """Starts listening to user inputs + buff scheduler."""
        print('\n[~] Started keyboard listener')
        self._alive.set()
        # 최신 설정 반영
        self.reload_buffs_from_config()
        # 스레드 시작
        self.thread.start()
        self._buff_thread.start()
        self.ready = True

    # (선택) 정리용. 있으면 더 안전.
    def stop(self, timeout=2.0):
        self._alive.clear()
        with self._cv:
            self._cv.notify_all()
        if self._buff_thread.is_alive():
            self._buff_thread.join(timeout=timeout)
        # 키 리스너 스레드는 루프가 while True라 별도 처리 없으면 계속 돎
        # 필요하면 enabled 플래그를 내려 루프 break 처리로 고치세요.

    def _main(self):
        """Constantly listens for user inputs and updates variables in config accordingly."""
        self.ready = True
        while True:
            try:
                if self.enabled:
                    if kb.is_pressed('f9'):
                        Listener.toggle_enabled()
                        # 키 뗄 때까지 살짝 대기 (디바운스)
                        while kb.is_pressed('f9'):
                            time.sleep(0.05)

                    elif kb.is_pressed('f8'):
                        x, y = config.player_pos_ab
                        # 좌표를 폼에 채우기
                        try:
                            form = config.gui.edit.form_panel
                            form.var_x.set(x)
                            form.var_y.set(y)
                        except Exception:
                            pass
                        # 디바운스
                        while kb.is_pressed('f8'):
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

        config.enabled = not config.enabled
        if config.enabled:
            handle_windows.activate_window(config.TITLE)
            # ── 봇 on 되는 시점에 버프 스케줄을 '지금부터' 시작하도록 next_at 초기화
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

    # ─────────────────────────────
    # Buff scheduler internals
    # ─────────────────────────────
    def _prime_buffs_on_enable(self):
        """F9로 최초/재시작할 때, 모든 버프의 next_at을 현재 시각 기준으로 재설정."""
        now = time.time()
        with self._cv:
            # 동시에 몰리지 않게 아주 작은 스태거(0~0.4s)도 줌
            stagger = 0.0
            for t in self._buff_tasks:
                t.next_at = now + 0.2 + stagger
                t.last_at = 0.0
                stagger += 0.1  # 0.1s 간격으로 순차 발사
            self._cv.notify_all()

    def _buff_loop(self):
        """별도 스레드: 버프 스케줄링/시전."""
        while self._alive.is_set():
            with self._cv:
                if not self._buff_tasks:
                    self._cv.wait(timeout=0.5)
                    continue
                now = time.time()
                due = min(t.next_at for t in self._buff_tasks)
                timeout = max(0.0, due - now)
                self._cv.wait(timeout=timeout)

            if not self._alive.is_set():
                break

            # 봇이 켜져 있을 때만 버프 사용 시작
            if not config.enabled:
                time.sleep(0.2)
                continue

            # ① 전투 중이면 버프 잠시 중지
            try:
                if getattr(config, "bot", None) and getattr(config.bot, "found_monster", False):
                    time.sleep(0.2)
                    continue
            except Exception:
                pass

            now = time.time()

            # ② 최소 1초 간격 유지: 마지막 발사로부터 1초 안 지났으면 기다림
            since = now - self._last_cast_ts
            if since < 1.0:
                time.sleep(1.0 - since)
                # 다시 조건 확인 후 진행
                continue

            # ③ 만기된 태스크 중 하나만 발사 (여러 개가 동시에 due여도
            #    전역 1초 간격 때문에 자연스레 시차가 생김)
            fired = False
            for t in self._buff_tasks:
                if t.next_at <= time.time():
                    self._fire_buff(t)
                    now2 = time.time()
                    t.last_at = now2
                    t.next_at = now2 + t.cooldown
                    self._last_cast_ts = now2  # 전역 간격 갱신
                    fired = True
                    break  # 한 번에 하나만
            if not fired:
                # 혹시라도 모든 next_at이 미래이면 살짝 쉼
                time.sleep(0.05)

    def _fire_buff(self, task: _BuffTask):
        """실제 키 입력. keyboard 실패 시 pyautogui로 백업."""
        try:
            kb.send(task.key)  # "f1", "q", "shift+a" 등
        except Exception:
            try:
                import pyautogui
                parts = [p.strip() for p in task.key.split("+")]
                pyautogui.hotkey(*parts)
            except Exception as e:
                print(f"[Listener] buff send failed ({task.key}): {e}")
        print(f"[Listener] buff -> {task.key}")
