import math
import threading
import time
import pyautogui
from src.common import config, utils, default_value as df
from contextlib import contextmanager
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


_pyauto_lock = threading.RLock()  # 모든 pyautogui 조작을 이 락으로 보호 권장

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
    # 멀티 모니터/스케일링 고려해서 현재 주 모니터 사이즈로 계산
    w, h = pyautogui.size()
    cx, cy = max(50, w // 2), max(50, h // 2)  # 모서리 안전 여유
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
        self._max_jump_tries = 1           # 점프 재시도 횟수 (원하면 1로 줄여도 됨)

        # 튜닝 파라미터
        self._stuck_eps_px = 1.0           # 이 픽셀 이하로만 움직이면 "안 움직임"으로 간주
        self._stuck_confirm_sec = 3     # 이 시간 이상 정체면 막힘 확정
        self._jump_cooldown = 5         # 점프 시도 간 최소 간격(스팸 방지)
        # self._last_jump_t = 0.0

        self.is_climbing = False          # 등반 중(부착~해제)
        self._last_attack_t = 0.0         # 최근 공격 시각(연타 속도 제한)
        self._attack_interval = 0.18      # 공격 최소 간격(초)

        self.stuck_attack_cnt = 0
        self.prev_char_pos    = None
        self.prev_action = ''
        self.can_attack = True

                # 강제 이동(스턱-대시) 파라미터
        self._fm_last_x = None
        self._fm_stuck_since = None
        self._fm_tries = 0
        self._fm_max_tries = 2        # 연속 시도 허용치
        self._fm_cooldown = 0.6       # 강제 이동 후 쿨다운(초)
        
        self._fm_last_exec_t = 0.0

        
        self._last_drop_t = 0.0
        self._drop_cooldown = 0.25  # 연속 드랍 방지

        self._attack_anim_sec = getattr(config.setting_data, 'attack_anim_sec', 0.35)  # 모션 길이(초)
        self.attack_anim_until = 0.0  # 모션이 끝나는 시각

        # Bot.__init__ 안
        self._drop_verify_timeout = 0.50   # 아래점프 후 관찰 시간(초)
        self._drop_verify_eps_px  = 3      # '내려갔다'로 인정할 최소 y 증가폭(px) - y가 아래로 갈수록 값 커진다고 가정

        self.input_lock = threading.RLock()
        config.input_lock = self.input_lock
    
   
            
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
        # 전투/등반 중에는 간섭하지 않음 (원하면 조건 완화 가능)
        if  self.up_down or self.is_climbing:
            self._fm_reset()
            return False

        pos = config.player_pos_ab
        if not pos:
            return False

        x, _ = pos
        now = time.time()

        # 첫 샘플링
        if self._fm_last_x is None:
            self._fm_last_x = x
            self._fm_stuck_since = None
            return False

        dx = abs(x - self._fm_last_x)
        self._fm_last_x = x

        # 쿨다운
        if (now - self._fm_last_exec_t) < self._fm_cooldown:
            return False

        if dx < self._stuck_eps_px:
            # 정체 시작
            if self._fm_stuck_since is None:
                self._fm_stuck_since = now
                return False

            # 충분히 오래 정체 → 강제 이동
            if (now - self._fm_stuck_since) >= self._stuck_confirm_sec:
                # 공격/불필요 입력 해제
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
              
                # 상태 업데이트
                self._fm_last_exec_t = now
                self._fm_stuck_since = None
                self._fm_tries += 1
                if self._fm_tries >= self._fm_max_tries:
                    # 반복 탈출 실패 시 완전 리셋(원하면 여기서 방향 전환 등 추가)
                    self._fm_tries = 0

                return True
            # 아직 정체 시간이 부족 → 대기
            return False

        # 정상 이동 중이면 리셋
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
        if self.shift_down or self.up_down:
            self._stuck_since = None
            self._last_x = None
            self._jump_tries = 0
            return False

        x = config.player_pos_ab[0]


        now = time.time()

        if self._stuck_since is None:
                self._stuck_since = now
        if self._last_x is None:
            self._last_x = x
            return False

        dx = abs(x - self._last_x)
        self._last_x = x
        
        if dx < self._stuck_eps_px:
            # 정체 시작/유지
            if self._stuck_since is None:
                self._stuck_since = now
                return False

            # 정체가 충분히 이어졌고, 쿨다운도 지났으면 점프
            if (now - self._stuck_since) >= self._stuck_confirm_sec :
                pyautogui.press(self.jump_key)     # ← 점프!
                self._last_jump_t = now
                self._jump_tries += 1

                # 여러 번 연속 시도 후엔 상태 리셋(원하면 방향전환 로직 붙여도 됨)
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
        # 필요시 조인
        # if self.thread and self.thread.is_alive():
        #     self.thread.join(timeout=2)

    def _main(self):
        self.ready = True
        
        while not (config.macro_shutdown_evt and config.macro_shutdown_evt.is_set()):
            try : 
                self.stuck_attack_cnt = 0
                self._ensure_key(self.attack_key, 'shift_down', False); 
                
                if config.enabled is False:
                    time.sleep(0.001)
                    continue
                
                if config.appear_other:
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
                        print(f'wp.y, cur_y : {wp.y}, {cur_y}')
                        
                        now = time.time()
                        if (now - self._last_drop_t) >= self._drop_cooldown:
                            self.drop_down()
                            self._last_drop_t = now
                        # 아래층으로 내려간 뒤 위치가 안정화될 시간을 잠깐 준다
                        time.sleep(0.15)
                    
                    elif wp.y + 6 < cur_y:
                        print("??")
                        if wp.action != "ladder":
                            print("???")
                            self.sync_waypoint_to_y()
                            
                        else:
                            if (not self.up_down) and (dx_abs > 12 or dy_abs > 6):   # 16은 맵에 맞춰 조정 가능(PREP_WIN*2 정도)
                                print("????")
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
                        self.release_all_keys()   # keyUp 정리 (여기도 pyautogui 호출 → 락 안에서)
                        _move_to_safe_center()    # 코너 대신 중앙으로 이동
                    finally:
                        pass  # FAILSAFE는 컨텍스트 매니저가 자동 복구

                time.sleep(0.3)
                

    def move_toward(self, target_x, action):
        if self.found_monster :
            return
        cur_x = config.player_pos_ab[0]
        dx = target_x - cur_x

        if action == "ladder":
            
            # 사다리용 접근 파라미터
            PREP_WIN = 6      # 이 이하로 가까워지면 감속/탭 이동
            SNAP_TOL = 0      # x 정렬 허용 오차
            ATTACH_WIN = 2    # 이 이하로 가까우면 즉시 부착 시도

            # 1) 멀면 일반 이동
            if dx < -PREP_WIN:
                self._new_direction('left')
                return
            elif dx > PREP_WIN:
                self._new_direction('right')
                return

            # 2) 접근 구간: 감속(탭 이동)으로 미세 정렬
            #    키다운 이동은 멈추고, 탭으로만 조정
            if self.left_down:  self._ensure_key('left',  'left_down',  False)
            if self.right_down: self._ensure_key('right', 'right_down', False)

            # 오차가 남았으면 탭으로 살짝 보정
            if abs(dx) > SNAP_TOL:
                self._nudge_toward(target_x, step_ms=0.02)

            # 3) 충분히 가까우면 바로 부착(Up+Jump) 실행
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
            
        STOP_TOL     = 0 if in_place else 2   # 이내면 완전히 정지
        PREC_TAP_WIN = 8  # 이내면 keydown 대신 탭으로 미세조정

        GO_TOL       = 6 if action != "jump" else 2  # 이보다 멀면 방향키를 눌러 이동(큰 이동)

        dx_abs = abs(dx)

        # 1) 목표 근처: 완전 정지
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

        # 3) 멀리 있을 때: 방향키를 확실히 눌러 이동
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
                abs(config.routine.items[i].y - cy),   # ① y 차
                abs(config.routine.items[i].x - cx)    # ② x 차
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
                # 이동 점프(횟수만큼)
                for _ in range(cnt):
                    pyautogui.press(self.jump_key)
                    self._ensure_key('left',  'left_down',  False)
                    self._ensure_key('right', 'right_down', False)
                    time.sleep(0.5) # 점프 후 멈추는 시간 

                return True
        
        elif wp.action == "ladder":
            if self.shift_down:
                self._ensure_key(self.attack_key, 'shift_down', False)

            # 0) x 미세 정렬(안전장치)
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

            # 1) 즉시 부착 시도 (Up+Jump)
            print("1) 즉시 부착 시도 (Up+Jump)")
            pyautogui.press(self.jump_key)   # 붙기 점프
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

                    # y 변화 감시(정체 체크)
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
        # 현재 y 기록 (검증용)
        start_y = None
        pos = config.player_pos_ab
        if pos:
            _, start_y = pos

        # 공격키/점프키 동시 입력 방지
        pyautogui.keyUp(self.attack_key)
        self.shift_down = False

        # 방향키는 굳이 누른 채일 필요 없음
        if self.left_down:
            pyautogui.keyUp('left');  self.left_down  = False
        if self.right_down:
            pyautogui.keyUp('right'); self.right_down = False

        # ↓ + 점프(단발)
        pyautogui.keyDown('down')
        pyautogui.press(self.jump_key)   # Alt 단발
        time.sleep(0.12)
        pyautogui.keyUp('down')

        # --- 여기서 '정말 내려갔는지' 짧게 관찰 ---
        if start_y is None:
            return  # 위치를 모르면 검증 스킵

        deadline = time.time() + self._drop_verify_timeout
        moved_down = False

        while time.time() < deadline:
            pos = config.player_pos_ab
            if pos:
                _, cur_y = pos
                # y가 아래로 갈수록 커진다고 가정: 충분히 증가했으면 성공
                if cur_y > start_y + self._drop_verify_eps_px:
                    moved_down = True
                    break
            time.sleep(0.02)  # 너무 빡세지 않게 폴링

        if not moved_down:
            # 일정 시간 관찰했는데 y가 안 내려갔다면 - 동기화 시도
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
            # shift_down 플래그는 False 유지

