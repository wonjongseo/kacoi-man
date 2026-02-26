import math
import threading
import time
import random
import pyautogui
import cv2
import mss
import numpy as np
from src.common import config, utils, default_value as df, handle_windows
from contextlib import contextmanager
from types import SimpleNamespace
class RoutePatrol:
    def __init__(self, items):
        self.items = items
        self.index = 0

    def current_wp(self):
       if not self.items:
           return None
       return self.items[self.index]

    def advance(self):
        if not self.items:
            self.index = 0
            return
        self.index = (self.index + 1) % len(self.items)
        config.gui.monitor.refresh_routine(current_index = self.index)


_pyauto_lock = threading.RLock()

@contextmanager
def _disable_failsafe_safely():
    with _pyauto_lock:
        old = pyautogui.FAILSAFE
        pyautogui.FAILSAFE = False
        try:
            yield
        finally:
            pyautogui.FAILSAFE = old

def _move_to_safe_center():

    w, h = pyautogui.size()
    cx, cy = max(50, w // 2), max(50, h // 2)
    pyautogui.moveTo(cx, cy, duration=0.05)


class Bot:
    def __init__(self):
        config.bot = self

        self.ready = False
        self.thread = threading.Thread(target=self._main)
        self.thread.daemon = True
        self.found_monster = False
        self.prev_direction = ''

        self.attack_key = getattr(config.setting_data ,'attack_key' , 'shift')
        self.jump_key = getattr(config.setting_data ,'jump_key' , 'alt')
       
        self.shift_down = self.left_down = self.up_down = self.right_down = self.z_down = False

        self._last_x = None
        self._stuck_since = None
        self._jump_tries = 0
        self._max_jump_tries = 1


        self._stuck_eps_px = 1.0
        self._stuck_confirm_sec = 3
        self._stuck_jump_confirm_sec = 1.5
       

        self.is_climbing = False
        self._last_attack_t = 0.0
        self._attack_interval = 0.18

        self.stuck_attack_cnt = 0
        self.prev_char_pos    = None
        self.prev_action = ''
        self.can_attack = True


        self._fm_last_x = None
        self._fm_stuck_since = None
        self._fm_tries = 0
        self._fm_max_tries = 2
        self._fm_cooldown = 0.6
        
        self._fm_last_exec_t = 0.0

        
        self._last_drop_t = 0.0
        self._drop_cooldown = 0.25

        self._attack_anim_sec = getattr(config.setting_data, 'attack_anim_sec', 0.35)
        self.attack_anim_until = 0.0


        self._drop_verify_timeout = 0.50
        self._drop_verify_eps_px  = 3

        self.input_lock = threading.RLock()
        config.input_lock = self.input_lock

        self._next_channel_switch_at = time.time() + float(df.CHANNEL_SWITCH_INTERVAL_SEC)
        self._channel_switch_pending = False
        self._menu_template = cv2.imread(utils.resource_path('assets/menu.png'), cv2.IMREAD_GRAYSCALE)
        self._channel_menu_template = cv2.imread(utils.resource_path('assets/channel.png'), cv2.IMREAD_GRAYSCALE)
        self._channel_frame_tl_template = cv2.imread(utils.resource_path('assets/channel_frame_lefttop.png'), cv2.IMREAD_GRAYSCALE)
        self._channel_frame_br_template = cv2.imread(utils.resource_path('assets/channel_frame_rightbottom.png'), cv2.IMREAD_GRAYSCALE)
        self._channel_is_fine_template = cv2.imread(utils.resource_path('assets/channel_is_fine.png'), cv2.IMREAD_COLOR)
        self._last_fine_channel_point = None
        self._change_template = cv2.imread(utils.resource_path('assets/change.png'), cv2.IMREAD_GRAYSCALE)
        self._ignore_monster_for_channel_switch = False
        self._last_other_forced_switch_t = 0.0
    
    def reload_runtime_settings(self):
        """Reload runtime keys/options from latest settings without recreating the bot."""
        s = getattr(config, "setting_data", None)
        if s is None:
            return
        self.attack_key = getattr(s, 'attack_key', self.attack_key) or self.attack_key
        self.jump_key = getattr(s, 'jump_key', self.jump_key) or self.jump_key
        self._attack_anim_sec = float(getattr(s, 'attack_anim_sec', self._attack_anim_sec) or self._attack_anim_sec)

   
             
    def _fm_reset(self):
        """강제 이동 스턱 상태 리셋"""
        self._fm_stuck_since = None
        self._fm_last_x = None
        self._fm_tries = 0

    def _probe_stuck_and_force_move(self):
        """
        x축 이동이 거의 없으면 짧은 대시(또는 점프-대시)로 탈출.
        반환값: 실제로 강제 이동을 수행하면 True, 아니면 False
        """

        if  self.up_down or self.is_climbing:
            self._fm_reset()
            return False

        pos = config.player_pos_ab
        if not pos:
            return False

        x, _ = pos
        now = time.time()


        if self._fm_last_x is None:
            self._fm_last_x = x
            self._fm_stuck_since = None
            return False

        dx = abs(x - self._fm_last_x)
        self._fm_last_x = x


        if (now - self._fm_last_exec_t) < self._fm_cooldown:
            return False

        if dx < self._stuck_eps_px:

            if self._fm_stuck_since is None:
                self._fm_stuck_since = now
                return False


            if (now - self._fm_stuck_since) >= self._stuck_confirm_sec:

                print("Kore?")
                self._ensure_key('z',     'z_down',     False)
                self._ensure_key(self.attack_key, 'shift_down', False)
                self._ensure_key('left',  'left_down',  False)
                self._ensure_key('right', 'right_down', False)

                escape_dir = self.prev_direction if self.prev_direction in ("left", "right") else "right"
                
                self._ensure_key(escape_dir, f'{escape_dir}_down', True)
                pyautogui.keyDown(self.jump_key)
                time.sleep(utils.rand_float(0.5, 0.8))
                self._ensure_key(escape_dir, f'{escape_dir}_down', False)
                pyautogui.keyUp(self.jump_key)
              

                self._fm_last_exec_t = now
                self._fm_stuck_since = None
                self._fm_tries += 1
                if self._fm_tries >= self._fm_max_tries:

                    self._fm_tries = 0

                return True

            return False


        self._fm_reset()
        return False

  
    def _attack_once(self):
        last_direction = 'right' if self.right_down else 'left'
        
        self._ensure_key(last_direction, f'{last_direction}_down', False)
        self._ensure_key(self.attack_key, 'shift_down', True)
        time.sleep(0.01)
        self._ensure_key(self.attack_key, 'shift_down', False)
        self._ensure_key(last_direction, f'{last_direction}_down', True)

    def _new_direction(self, new_direction):
        self._ensure_key('z',  'z_down', False)
        self._ensure_key(new_direction,  f'{new_direction}_down', True)
        
        if self.prev_direction and self.prev_direction != new_direction:
            self._ensure_key(self.prev_direction,  f'{self.prev_direction}_down', False)
        self.prev_direction = new_direction
        self._ensure_key('z',  'z_down', True)

    def _probe_stuck_and_jump(self):
        moving_horizontally = bool(self.left_down or self.right_down)
        if self.shift_down or self.up_down or self.is_climbing or (not moving_horizontally):
            self._stuck_since = None
            self._last_x = None
            self._jump_tries = 0
            return False

        now = time.time()
        if now < self.attack_anim_until:
            self._stuck_since = None
            self._last_x = None
            self._jump_tries = 0
            return False

        x = config.player_pos_ab[0]

        if self._stuck_since is None:
                self._stuck_since = now
        if self._last_x is None:
            self._last_x = x
            return False

        dx = abs(x - self._last_x)
        self._last_x = x
        
        if dx < self._stuck_eps_px:

            if self._stuck_since is None:
                self._stuck_since = now
                return False


            if (now - self._stuck_since) >= self._stuck_jump_confirm_sec :
                pyautogui.press(self.jump_key)
                self._last_jump_t = now
                self._jump_tries += 1


                if self._jump_tries >= self._max_jump_tries:
                    self._stuck_since = None
                    self._jump_tries = 0
                return True
        else:
            self._stuck_since = None
            self._jump_tries = 0
        return False
    
    def start(self):
        print('\n[~] Started main bot loop')
        self.thread.start()

    def _nudge_toward(self, target_x, step_ms=0.02):
        print("_nudge_toward")
        """한 번의 짧은 탭으로 x를 미세 조정."""
        cx = config.player_pos_ab[0]
        if target_x < cx:           
            self._ensure_key('left', 'left_down', True); 
            time.sleep(step_ms);
            self._ensure_key('left', 'left_down', False)
        elif target_x > cx:
            self._ensure_key('right', 'right_down', True); 
            time.sleep(step_ms); 
            self._ensure_key('right', 'right_down', False); 

    def stop(self):
        if config.macro_shutdown_evt:
            config.macro_shutdown_evt.set()


    def _main(self):
        self.ready = True
        
        while not (config.macro_shutdown_evt and config.macro_shutdown_evt.is_set()):
            try : 
                self.stuck_attack_cnt = 0
                self._ensure_key(self.attack_key, 'shift_down', False); 
                
                if config.enabled is False:
                    time.sleep(0.001)
                    continue

                now = time.time()
                if now >= self._next_channel_switch_at:
                    self._channel_switch_pending = True

                # Hard priority: once due, do not run normal routine until channel switch succeeds.
                if self._channel_switch_pending:
                    switched = self._run_channel_switch_sequence()
                    if switched:
                        self._channel_switch_pending = False
                        self._next_channel_switch_at = time.time() + float(df.CHANNEL_SWITCH_INTERVAL_SEC)
                    else:
                        # keep pending; retry soon and block all other actions
                        time.sleep(max(0.5, float(df.CHANNEL_SWITCH_WAIT_CHECK_SEC)))
                    time.sleep(0.2)
                    continue
                 
                if config.appear_other:
                    # If another player is detected right after channel move, jump to a different channel immediately.
                    if (now - self._last_other_forced_switch_t) >= 5.0:
                        self._last_other_forced_switch_t = now
                        switched = self._run_channel_switch_sequence(skip_safe_move=True)
                        self._next_channel_switch_at = time.time() + (
                            float(df.CHANNEL_SWITCH_INTERVAL_SEC) if switched else float(df.CHANNEL_SWITCH_RETRY_SEC)
                        )
                    self.release_all_keys()
                    time.sleep(0.001)
                    continue

                if self.found_monster and getattr(config, 'attack_in_capture', True):
                    time.sleep(0.03)
                    continue
                        
                else:
                    self._ensure_key('z', 'z_down', True)
                    if not config.routine or not getattr(config.routine, "items", None):
                        time.sleep(0.05)
                        continue
                    wp = config.routine.current_wp()
                    if wp is None:
                        time.sleep(0.05)
                        continue
                    cur_x, cur_y = config.player_pos_ab

                    dx = wp.x - cur_x
                    dy = wp.y - cur_y
                    dx_abs = abs(dx)
                    dy_abs = abs(dy)

                    self.can_attack = not self.up_down
                    
                    if wp.action != "down" and (wp.y > cur_y + 6):
                        
                        now = time.time()
                        if (now - self._last_drop_t) >= self._drop_cooldown:
                            self.drop_down()
                            self._last_drop_t = now

                        time.sleep(0.15)
                    
                    elif wp.y + 6 < cur_y:
                        if wp.action != "ladder":
                            self.sync_waypoint_to_y()
                            
                        else:
                            if (not self.up_down) and (dx_abs > 12 or dy_abs > 6):
                                self.sync_waypoint_to_y()
                                
                    
                    if self.reached(wp):
                        if self.found_monster :
                            continue
                        if self.do_action(wp):
                            self.prev_action = wp.action
                            config.routine.advance()
                    else:
                        self.move_toward(wp.x, wp.action)
                        triggered = self._probe_stuck_and_jump()
                        
                        if not triggered:
                            self._probe_stuck_and_force_move()

                    time.sleep(0.15)
            except pyautogui.FailSafeException:
                print("[FAILSAFE] 모서리 감지 → 안전 복구 시도")

                with _disable_failsafe_safely():
                    try:
                        self.release_all_keys()
                        _move_to_safe_center()
                    finally:
                        pass

                time.sleep(0.3)
                 
    def _grab_capture_window(self):
        cap = getattr(config, "capture", None)
        if cap is None or not getattr(cap, "window", None):
            return None, None
        win = cap.window
        monitor = {
            "left": int(win.get("left", 0)),
            "top": int(win.get("top", 0)),
            "width": int(win.get("width", 0)),
            "height": int(win.get("height", 0)),
        }
        if monitor["width"] <= 0 or monitor["height"] <= 0:
            return None, None
        with mss.mss() as sct:
            frame = np.array(sct.grab(monitor))[:, :, :3]
        return frame, monitor

    def _click_template_in_window(self, template, timeout_sec=5.0):
        if template is None:
            return False
        threshold = float(df.CHANNEL_SWITCH_MATCH_THRESHOLD)
        deadline = time.time() + timeout_sec
        while time.time() < deadline and config.enabled:
            frame, monitor = self._grab_capture_window()
            if frame is None:
                time.sleep(0.1)
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            th, tw = template.shape[:2]
            fh, fw = gray.shape[:2]
            if th > fh or tw > fw:
                time.sleep(0.1)
                continue
            res = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            if max_val >= threshold:
                x = monitor["left"] + max_loc[0] + (tw // 2)
                y = monitor["top"] + max_loc[1] + (th // 2)
                pyautogui.click(x, y)
                return True
            time.sleep(0.1)
        return False

    def _wait_character_name_visible(self, timeout_sec):
        name_path = getattr(config.setting_data.templates.character, "name", "")
        if not name_path:
            return False
        name_template = cv2.imread(name_path, cv2.IMREAD_GRAYSCALE)
        if name_template is None:
            return False

        threshold = float(df.CHANNEL_SWITCH_MATCH_THRESHOLD)
        deadline = time.time() + timeout_sec
        while time.time() < deadline and config.enabled:
            frame = getattr(config.capture, "frame", None)
            if frame is None:
                time.sleep(0.1)
                continue
            try:
                if len(frame.shape) == 3 and frame.shape[2] == 4:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
                else:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            except Exception:
                time.sleep(0.1)
                continue
            th, tw = name_template.shape[:2]
            fh, fw = gray.shape[:2]
            if th > fh or tw > fw:
                time.sleep(0.1)
                continue
            res = cv2.matchTemplate(gray, name_template, cv2.TM_CCOEFF_NORMED)
            if np.max(res) >= threshold:
                return True
            time.sleep(0.1)
        return False

    def _find_best_match(self, gray, template, threshold):
        if template is None:
            return None
        th, tw = template.shape[:2]
        gh, gw = gray.shape[:2]
        if th > gh or tw > gw:
            return None
        res = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val < threshold:
            return None
        return max_loc, max_val, (tw, th)

    def _pick_random_fine_channel_in_frame(self, timeout_sec=5.0):
        threshold = float(df.CHANNEL_SWITCH_MATCH_THRESHOLD)
        deadline = time.time() + timeout_sec

        while time.time() < deadline and config.enabled:
            frame, monitor = self._grab_capture_window()
            if frame is None:
                time.sleep(0.1)
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            tl_m = self._find_best_match(gray, self._channel_frame_tl_template, threshold)
            br_m = self._find_best_match(gray, self._channel_frame_br_template, threshold)
            if tl_m is None or br_m is None:
                time.sleep(0.1)
                continue

            (tl_xy, _, tl_wh) = tl_m
            (br_xy, _, br_wh) = br_m
            x1 = int(tl_xy[0] + tl_wh[0])
            y1 = int(tl_xy[1] + tl_wh[1])
            x2 = int(br_xy[0])
            y2 = int(br_xy[1])

            if x2 <= x1 or y2 <= y1:
                time.sleep(0.1)
                continue

            roi = frame[y1:y2, x1:x2]
            fine = self._channel_is_fine_template
            if fine is None:
                return False, None
            fh, fw = fine.shape[:2]
            rh, rw = roi.shape[:2]
            if fh > rh or fw > rw:
                time.sleep(0.1)
                continue

            res = cv2.matchTemplate(roi, fine, cv2.TM_CCOEFF_NORMED)
            ys, xs = np.where(res >= threshold)
            if len(xs) == 0:
                time.sleep(0.1)
                continue

            # Build candidate centers and reduce near-duplicates.
            raw = []
            for (rx, ry) in zip(xs, ys):
                score = float(res[ry, rx])
                cx = int(rx + fw // 2)
                cy = int(ry + fh // 2)
                raw.append((score, cx, cy))
            raw.sort(reverse=True, key=lambda t: t[0])

            dedup = []
            min_dist = max(8, min(fw, fh) // 2)
            for score, cx, cy in raw:
                if all(((cx - ox) ** 2 + (cy - oy) ** 2) >= (min_dist * min_dist) for _, ox, oy in dedup):
                    dedup.append((score, cx, cy))

            candidates = dedup[:]
            if self._last_fine_channel_point is not None and len(candidates) > 1:
                lx, ly = self._last_fine_channel_point
                filtered = [(s, cx, cy) for (s, cx, cy) in candidates if abs(cx - lx) + abs(cy - ly) > 2]
                if filtered:
                    candidates = filtered

            _, pick_x, pick_y = random.choice(candidates)
            self._last_fine_channel_point = (pick_x, pick_y)

            abs_x = monitor["left"] + x1 + pick_x
            abs_y = monitor["top"] + y1 + pick_y
            pyautogui.click(abs_x, abs_y)
            return True, "channel_is_fine"

        return False, None

    def _wait_character_name_reloaded(self, timeout_sec):
        name_path = getattr(config.setting_data.templates.character, "name", "")
        if not name_path:
            return False
        name_template = cv2.imread(name_path, cv2.IMREAD_GRAYSCALE)
        if name_template is None:
            return False

        threshold = float(df.CHANNEL_SWITCH_MATCH_THRESHOLD)
        start_t = time.time()
        deadline = time.time() + timeout_sec
        seen_disappear = False

        while time.time() < deadline and config.enabled:
            frame = getattr(config.capture, "frame", None)
            if frame is None:
                time.sleep(0.1)
                continue
            try:
                if len(frame.shape) == 3 and frame.shape[2] == 4:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
                else:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            except Exception:
                time.sleep(0.1)
                continue

            th, tw = name_template.shape[:2]
            fh, fw = gray.shape[:2]
            if th > fh or tw > fw:
                time.sleep(0.1)
                continue

            res = cv2.matchTemplate(gray, name_template, cv2.TM_CCOEFF_NORMED)
            max_val = float(np.max(res))
            visible = bool(max_val >= threshold)

            if not visible:
                if not seen_disappear:
                    print(f"[Bot] name hidden (loading?) at +{time.time() - start_t:.2f}s")
                seen_disappear = True
            elif seen_disappear and visible:
                print(
                    f"[Bot] name detected at +{time.time() - start_t:.2f}s "
                    f"(score={max_val:.3f}, threshold={threshold:.3f})"
                )
                return True
            time.sleep(0.1)

        print(f"[Bot] name detect timeout after {timeout_sec:.1f}s")
        return False

    def _apply_enable_like_runtime_reset(self):
        """
        Apply the same runtime refresh path used when pressing F9 to enable:
        focus window, rebind to (0,0), reload runtime settings, and prime buffs.
        """
        handle_windows.activate_window(config.TITLE)

        if getattr(config, "gui", None) and hasattr(config.gui, "monitor"):
            config.gui.monitor.refresh_routine()

        if hasattr(self, "reload_runtime_settings"):
            self.reload_runtime_settings()

        cap = getattr(config, "capture", None)
        if cap is not None and hasattr(cap, "rebind_window"):
            cap.rebind_window(force_move=True)

        listener = getattr(config, "listener", None)
        if listener is not None:
            if hasattr(listener, "reload_buffs_from_config"):
                listener.reload_buffs_from_config()
            if hasattr(listener, "_prime_buffs_on_enable"):
                listener._prime_buffs_on_enable()

    def _run_channel_switch_sequence(self, skip_safe_move=False):
        right_hold_started = False
        potion_paused_for_switch = False
        try:
            # During channel-change loading, black screen is expected.
            config.black_screen_suppress_until = time.time() + float(df.CHANNEL_SWITCH_LOAD_TIMEOUT_SEC) + 5.0
            config.potion_suppress_until = time.time() + float(df.CHANNEL_SWITCH_LOAD_TIMEOUT_SEC) + 5.0
            old_attack_in_capture = getattr(config, "attack_in_capture", True)
            config.attack_in_capture = False
            self._ignore_monster_for_channel_switch = True

            if (not skip_safe_move) and (not self._move_to_safe_ladder_before_switch()):
                print("[Bot] channel switch failed: could not reach safe ladder waypoint")
                return False

            self.release_all_keys()
            handle_windows.activate_window(config.TITLE)
            time.sleep(0.05)

            if not self._click_template_in_window(self._menu_template, timeout_sec=5.0):
                print("[Bot] channel switch failed: menu not found")
                return False
            time.sleep(1.0)

            if not self._click_template_in_window(self._channel_menu_template, timeout_sec=5.0):
                print("[Bot] channel switch failed: channel menu not found")
                return False
            time.sleep(1.0)

            # Pick one random "available channel" icon in the channel frame region.
            picked, channel_name = self._pick_random_fine_channel_in_frame(timeout_sec=5.0)
            if not picked:
                print("[Bot] channel switch failed: no channel_is_fine found in channel frame")
                return False

            if not self._click_template_in_window(self._change_template, timeout_sec=5.0):
                print("[Bot] channel switch failed: change not found")
                return False

            # Pause potion checks during channel-change loading.
            config.potion_runtime_enabled = False
            potion_paused_for_switch = True

            # Keep moving right after pressing change until loading completes.
            self._ensure_key('right', 'right_down', True)
            right_hold_started = True

            # Success means character name disappeared (loading) then came back.
            if not self._wait_character_name_reloaded(timeout_sec=float(df.CHANNEL_SWITCH_LOAD_TIMEOUT_SEC)):
                print("[Bot] channel switch failed: character name was not reloaded")
                return False

            self._ensure_key('right', 'right_down', False)
            right_hold_started = False
            config.potion_runtime_enabled = True
            potion_paused_for_switch = False

            # After character name is visible again, run the same init path as F9 ON.
            self._apply_enable_like_runtime_reset()
            config.appear_other = False

            print(f"[Bot] channel switch done -> {channel_name}")
            return True
        except Exception as e:
            print(f"[Bot] channel switch exception: {e}")
            return False
        finally:
            if right_hold_started:
                self._ensure_key('right', 'right_down', False)
            if potion_paused_for_switch:
                config.potion_runtime_enabled = True
            self._ignore_monster_for_channel_switch = False
            config.attack_in_capture = old_attack_in_capture

    def _is_channel_switch_position_ready(self):
        tx = int(getattr(df, "CHANNEL_SWITCH_POS_X", -1))
        ty = int(getattr(df, "CHANNEL_SWITCH_POS_Y", -1))
        tol_x = int(getattr(df, "CHANNEL_SWITCH_POS_TOL_X", 8))
        tol_y = int(getattr(df, "CHANNEL_SWITCH_POS_TOL_Y", 8))

        # If both are negative, do not enforce position gating.
        if tx < 0 and ty < 0:
            return True

        pos = getattr(config, "player_pos_ab", None)
        if not pos:
            return False
        cx, cy = pos

        if tx >= 0 and abs(cx - tx) > tol_x:
            return False
        if ty >= 0 and abs(cy - ty) > tol_y:
            return False
        return True

    def _move_to_safe_ladder_before_switch(self):
        wp = SimpleNamespace(
            x=int(getattr(df, "CHANNEL_SWITCH_SAFE_LADDER_X", 35)),
            y=int(getattr(df, "CHANNEL_SWITCH_SAFE_LADDER_Y", 119)),
            end_y=int(getattr(df, "CHANNEL_SWITCH_SAFE_LADDER_END_Y", 84)),
            action="ladder",
            count=1,
            in_place=False,
        )
        deadline = time.time() + float(getattr(df, "CHANNEL_SWITCH_SAFE_LADDER_TIMEOUT_SEC", 25))

        while time.time() < deadline and config.enabled:
            pos = getattr(config, "player_pos_ab", None)
            if not pos:
                time.sleep(0.05)
                continue

            self.found_monster = False
            if self.reached(wp):
                if self.do_action(wp):
                    return True
            else:
                self.move_toward(wp.x, wp.action)
                if not self._probe_stuck_and_jump():
                    self._probe_stuck_and_force_move()
            time.sleep(0.05)

        return False

    def move_toward(self, target_x, action):
        if self.found_monster and not self._ignore_monster_for_channel_switch:
            return
        cur_x = config.player_pos_ab[0]
        dx = target_x - cur_x

        if action == "ladder":
            

            PREP_WIN = 6
            SNAP_TOL = 0
            ATTACH_WIN = 2


            if dx < -PREP_WIN:
                self._new_direction('left')
                return
            elif dx > PREP_WIN:
                self._new_direction('right')
                return



            if self.left_down:  self._ensure_key('left',  'left_down',  False)
            if self.right_down: self._ensure_key('right', 'right_down', False)


            if abs(dx) > SNAP_TOL:
                self._nudge_toward(target_x, step_ms=0.02)


            if abs(dx) <= ATTACH_WIN:
                self._ensure_key('up', 'up_down', True)
                time.sleep(0.02)
                pyautogui.press(self.jump_key)         
                self.is_climbing = True
                self.sync_direction()
            return

        in_place = False
        if action == "jump":
            wp = config.routine.current_wp()
            in_place = getattr(wp, 'in_place', False)
            
        STOP_TOL     = 0 if in_place else 2
        PREC_TAP_WIN = 8

        GO_TOL       = 6 if action != "jump" else 2

        dx_abs = abs(dx)


        if action == "ladder" or (action == 'jump' and in_place) :
            if dx_abs <= STOP_TOL:
                if self.left_down:  self._ensure_key('left',  'left_down',  False)
                if self.right_down: self._ensure_key('right', 'right_down', False)
                self.sync_direction()
                return
            if dx_abs <= PREC_TAP_WIN:
                if self.left_down:  self._ensure_key('left',  'left_down',  False)
                if self.right_down: self._ensure_key('right', 'right_down', False)
                self._nudge_toward(target_x, step_ms=0.018)
                return


        if dx < -GO_TOL:
            self._new_direction('left')
        elif dx > GO_TOL:
            self._new_direction('right')
        else:
            self.sync_direction()
            

    def sync_direction(self):
        if self.prev_direction == 'right':
            self._ensure_key('left',  'left_down', True)
            time.sleep(utils.rand_float(0.1,0.3))
            self._ensure_key('left',  'left_down', False)
        else:
            self._ensure_key('right',  'right_down', True)
            time.sleep(utils.rand_float(0.1,0.3))
            self._ensure_key('right',  'right_down', False)

    def sync_waypoint_to_y(self):
        print("Called sync_waypoint_to_y")
        cx, cy = config.player_pos_ab

        best_i = min(
            range(len(config.routine.items)),
            key=lambda i: (
                abs(config.routine.items[i].y - cy),
                abs(config.routine.items[i].x - cx)
            )
        )
        
        if best_i != config.routine.index:
            config.routine.index = best_i
            config.gui.monitor.refresh_routine(best_i)
            print(f"[INFO] WP 재동기화(Y 기준) → #{best_i+1} (x:{cx}, y:{cy})")
    
    def reached(self, wp):
        """웨이포인트에 도달했는지 여부를 반환"""
        cx, cy = config.player_pos_ab
        dx = abs(cx - wp.x)
        dy = abs(cy - wp.y)
        hit = False
        
        if wp.action == "ladder":
            if not (self.left_down or self.right_down):
                tol = 0
            else:
                if self.prev_action == "jump" :
                    tol = 0
                else:    
                    tol = df.REACH_LADDER_MOVING 
            # tol = 0  if not (self.left_down or self.right_down) else df.REACH_LADDER_MOVING
            hit=  dx <= tol
        elif wp.action == "jump":
            tol = 0 if wp.in_place else (1 if self.prev_action == 'ladder' else 5)
            return dx <= tol
        elif wp.action == "down":
            tol = 3
            return dx <= tol
        else:
            hit=  dx <= 5 and dy <= 5
        
        return hit
    
    def do_action(self,  wp=None):
        if wp.action == "jump":
            in_place = getattr(wp, "in_place", False)
            cnt = wp.count
            if in_place:
                self._ensure_key('left',  'left_down',  False)
                self._ensure_key('right', 'right_down', False)
                self._ensure_key(self.attack_key, 'shift_down', False)

                in_place_delay = getattr(wp, "in_place_delay", df.IN_PLACE_DELAY)
                time.sleep(in_place_delay)

                for _ in range(cnt):
                    pyautogui.press(self.jump_key)
                    time.sleep(0.5)
                return True
            else:

                for _ in range(cnt):
                    pyautogui.press(self.jump_key)
                    self._ensure_key('left',  'left_down',  False)
                    self._ensure_key('right', 'right_down', False)
                    time.sleep(0.5)

                return True
        
        elif wp.action == "ladder":
            if self.shift_down:
                self._ensure_key(self.attack_key, 'shift_down', False)


            success = False
            target_x = wp.x
            
            if self.left_down == False and self.right_down == False:
                while True:
                    while self.found_monster :
                        self._ensure_key('z', 'z_down', False); 
                        self._ensure_key(self.attack_key, 'shift_down', True); 
                    
                    self._ensure_key(self.attack_key, 'shift_down', False); 


                    cx, _ = config.player_pos_ab
                    if abs(cx - target_x) == 0:
                        break
                    self._nudge_toward(target_x, step_ms=0.1)
                    time.sleep(0.01)


            print("1) 즉시 부착 시도 (Up+Jump)")
            pyautogui.press(self.jump_key)
            self._ensure_key('up', 'up_down', True)
            time.sleep(0.02)
            self.is_climbing = True
            try:
                target_y  = wp.end_y if wp else None
                prev_cy   = None
                stall_t   = time.time()

                while True:
                    self._ensure_key('left',  'left_down', False)
                    self._ensure_key('right', 'right_down', False)
                    pos = config.player_pos_ab
                    
                    _, cy = pos

                    if target_y is not None and cy <= target_y:
                        success = True
                        break


                    if prev_cy is None or abs(cy - prev_cy) > 1:
                        prev_cy = cy
                        stall_t = time.time()

                    if time.time() - stall_t > 0.6:
                        self._nudge_toward(target_x, step_ms=0.02)
                        return False

                    time.sleep(0.03)
            finally:
                time.sleep(0.25)
                self._ensure_key('up',  'up_down', False)
                self.is_climbing = False
                if success == False:
                    df = 1 if utils.bernoulli(0.5) else -1
                    self._nudge_toward(target_x - df)
               
            return success

        elif wp.action == 'down' : 
            print("wp.action == 'down'")
            self.release_all_keys()
            self.drop_down()
        return True
    
    def drop_down(self):
        """↓+Jump(Alt)로 아래 플랫폼으로 내려가기 — 공격키/방향키와 충돌 방지
        내려가지 않았으면 sync_waypoint_to_y()를 호출한다.
        """

        start_y = None
        pos = config.player_pos_ab
        if pos:
            _, start_y = pos


        pyautogui.keyUp(self.attack_key)
        self.shift_down = False


        if self.left_down:
            pyautogui.keyUp('left');  self.left_down  = False
        if self.right_down:
            pyautogui.keyUp('right'); self.right_down = False


        pyautogui.keyDown('down')
        pyautogui.press(self.jump_key)
        time.sleep(0.12)
        pyautogui.keyUp('down')


        if start_y is None:
            return

        deadline = time.time() + self._drop_verify_timeout
        moved_down = False

        while time.time() < deadline:
            pos = config.player_pos_ab
            if pos:
                _, cur_y = pos

                if cur_y > start_y + self._drop_verify_eps_px:
                    moved_down = True
                    break
            time.sleep(0.02)

        if not moved_down:

            try:
                self.sync_waypoint_to_y()
            except Exception as e:
                print(f"[WARN] sync_waypoint_to_y() failed: {e}")

    def mark_attack(self, anim_sec=None):
        sec = anim_sec or self._attack_anim_sec
        now = time.time()
        self._last_attack_t = now
        self.attack_anim_until = now + sec

    def release_all_keys(self):
        with self.input_lock:
            for k in (self.attack_key, 'left', 'right', 'up', 'down', 'z'):
                pyautogui.keyUp(k)
            self.shift_down = self.left_down = self.up_down = self.right_down = self.z_down = False


    def _ensure_key(self, key, flag_attr, value):
        try:
            with self.input_lock:
                cur = getattr(self, flag_attr)
            if value:
                if not cur:
                    pyautogui.keyDown(key)
                    setattr(self, flag_attr, True)
            else:
                if cur:
                    pyautogui.keyUp(key)
                    setattr(self, flag_attr, False)
        except:
            print(f'Except at key, flag_attr, value : {key}, {flag_attr}, {value}')
            
    
    def face(self, to_dir: str):
        """한쪽만 눌린 방향 상태 보장 (락 포함)."""
        with self.input_lock:
            if to_dir == 'left':
                self._ensure_key('right', 'right_down', False)
                self._ensure_key('left',  'left_down',  True)
                self.prev_direction = 'left'
            else:
                self._ensure_key('left',  'left_down',  False)
                self._ensure_key('right', 'right_down', True)
                self.prev_direction = 'right'

    def tap_attack(self, dur=0.01):
        """홀드가 아닌 '탁' 한 번. 내부 플래그를 홀드로 남기지 않음."""
        with self.input_lock:
            pyautogui.keyUp(self.jump_key)
            if self.shift_down:
                pyautogui.keyUp(self.attack_key)
                self.shift_down = False
            pyautogui.keyDown(self.attack_key)
            time.sleep(dur)
            pyautogui.keyUp(self.attack_key)
