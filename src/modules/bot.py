import math
import threading
import time
import pyautogui
from src.common import config, utils, default_value as df

class RoutePatrol:
    def __init__(self, items):
        self.items = items
        self.index = 0

    def current_wp(self):
       return self.items[self.index]

    def advance(self):
        self.index = (self.index + 1) % len(self.items)
        config.gui.monitor.refresh_routine(current_index = self.index)


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
        self._fm_eps_px = 1.5         # 이 픽셀 이하 이동이면 '정체'로 간주
        self._fm_confirm_sec = 0.25   # 정체가 이 시간 이상 지속되면 강제 이동
        self._fm_press_sec = 0.32     # 방향키 홀드 시간(초) — 맵에 맞춰 조정
        self._fm_cooldown = 0.6       # 강제 이동 후 쿨다운(초)
        
        self._fm_last_exec_t = 0.0

        
        self._last_drop_t = 0.0
        self._drop_cooldown = 0.25  # 연속 드랍 방지

        self._attack_anim_sec = getattr(config.setting_data, 'attack_anim_sec', 0.35)  # 모션 길이(초)
        self.attack_anim_until = 0.0  # 모션이 끝나는 시각

        self.input_lock = threading.RLock()
        config.input_lock = self.input_lock
    
    def _face_only(self, to_dir: str):
        """공격키/기타키 건드리지 않고 '방향키'만 정리해서 바라보게 함"""
        if to_dir == 'left':
            self._ensure_key('right', 'right_down', False)
            self._ensure_key('left',  'left_down',  True)
            time.sleep(0.2)
            self.prev_direction = 'left'
        else:
            self._ensure_key('left',  'left_down',  False)
            self._ensure_key('right', 'right_down', True)
            self.prev_direction = 'right'
            
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

        if dx < self._fm_eps_px:
            # 정체 시작
            if self._fm_stuck_since is None:
                self._fm_stuck_since = now
                return False

            # 충분히 오래 정체 → 강제 이동
            if (now - self._fm_stuck_since) >= self._fm_confirm_sec:
                # 공격/불필요 입력 해제
                self._ensure_key('z',     'z_down',     False)
                self._ensure_key(self.attack_key, 'shift_down', False)
                self._ensure_key('left',  'left_down',  False)
                self._ensure_key('right', 'right_down', False)

                escape_dir = self.prev_direction
                
                self._ensure_key(escape_dir, f'{escape_dir}_down', True)
                pyautogui.keyDown(self.jump_key)
                time.sleep(self._fm_press_sec)
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

    
    
    def _weave_attack(self):
    # 이동/등반 로직을 중단하지 않고, “가능할 때만” 한 번 툭 치기
        if not (self.found_monster and self.can_attack):
            return

        now = time.time()
        if now - self._last_attack_t < self._attack_interval:
            return

        # 바라보는 방향 폴백
        face = (
            'right' if (self.right_down and not self.left_down) else
            'left'  if (self.left_down  and not self.right_down) else
            (self.prev_direction or 'right')
        )
        self._ensure_key(face, f'{face}_down', True)
        self._attack_once()
        self._last_attack_t = now

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
        print(f'cx, target_x : {cx}, {target_x}')
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
                # if self.is_climbing == False and self.found_monster :
                    # now = time.time()
                    # if self.monster_dir == 'back' and (now - self._last_turn_t) >= self._turn_interval:
                    #     # 현재 바라보는 반대쪽으로 한 번만 돌기
                    #     if self.right_down and not self.left_down:
                    #         self._face_only('left')
                    #     elif self.left_down and not self.right_down:
                    #         self._face_only('right')
                    #     self._last_turn_t = now
                        
                    # self._ensure_key('z', 'z_down', False); 
                    # self._ensure_key(self.attack_key, 'shift_down', True); 

                    # #a() 
                    # time.sleep(0.1)
                    time.sleep(0.03)
                    continue
                        
                else:
                    self._ensure_key('z', 'z_down', True)
                    wp = config.routine.current_wp()
                    target_x, target_y, act = wp.x, wp.y, wp.action
                    cur_x, cur_y = config.player_pos_ab

                    dx = target_x - cur_x
                    dy = target_y - cur_y
                    dx_abs = abs(dx)
                    dy_abs = abs(dy)

                    # 공격 가능 여부는 "거리"로 결정
                    
                    self.can_attack = not self.up_down
                    if act != "down" and (target_y > cur_y + 6):
                        now = time.time()
                        if (now - self._last_drop_t) >= self._drop_cooldown:
                            self.drop_down()
                            self._last_drop_t = now
                        # 아래층으로 내려간 뒤 위치가 안정화될 시간을 잠깐 준다
                        time.sleep(0.15)
                    
                    elif target_y + 6 < cur_y:
                        print("??")
                        if act != "ladder":
                            print("???")
                            self.sync_waypoint_to_y()
                            
                        else:
                            # X가 충분히 멀다(=사다리 접근도 못하는 위치) + Up 미홀드(등반중 아님) → 재동기화 허용 
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
                        self.move_toward(target_x, act)
                        triggered = self._probe_stuck_and_jump()
                        
                        if not triggered:
                            self._probe_stuck_and_force_move()
                
                        # self._weave_attack()

                    time.sleep(0.15)
            except pyautogui.FailSafeException:
                pyautogui.FAILSAFE = False
                try:
                    self.release_all_keys()
                    pyautogui.moveTo(config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
                finally:
                    pyautogui.FAILSAFE = True     # 2) 다시 켜 주기
                time.sleep(1)  
                

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

            # # 공격키 해제(밀림 방지)
            # self._ensure_key('z', 'z_down', False)

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
                print("abs(dx) > SNAP_TOL:")
                self._nudge_toward(target_x, step_ms=0.02)

            # 3) 충분히 가까우면 바로 부착(Up+Jump) 실행
            if abs(dx) <= ATTACH_WIN:
                print("if abs(dx) <= ATTACH_WIN:")
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
                print(" dx_abs <= PREC_TAP_WIN:")
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
        cx, cy = config.player_pos_ab

        best_i = min(
            range(len(config.routine.items)),
            key=lambda i: (
                abs(config.routine.items[i].y - cy),   # ① y 차
                abs(config.routine.items[i].x - cx)    # ② x 차
            )
        )
        print(f'best_i : {best_i}')
        print(f'config.routine.index : {config.routine.index}')
        
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
            tol = 0  if not (self.left_down or self.right_down) else df.REACH_LADDER_MOVING
            hit=  dx <= tol
        elif wp.action == "jump":
            tol = 0 if wp.in_place else (2 if self.prev_action == 'ladder' else 5)
            return dx <= tol
        elif wp.action == "down":
            tol = 3
            return dx <= tol
        else:
            hit=  dx <= 5 and dy <= 5
        
        return hit
    
    def do_action(self,  wp=None):
        if self.found_monster :
            return
        if wp.action == "jump":
            in_place = getattr(wp, "in_place", False)
            cnt = wp.count
            if in_place:
                # 움직임 키 완전히 해제하고 제자리 점프만
                self._ensure_key('left',  'left_down',  False)
                self._ensure_key('right', 'right_down', False)
                self._ensure_key(self.attack_key, 'shift_down', False)

                in_place_delay = getattr(wp, "in_place_delay", df.IN_PLACE_DELAY)
                time.sleep(in_place_delay)

                for _ in range(cnt):
                    pyautogui.press(self.jump_key)
                    time.sleep(0.5)
                print("RETURN")
                return True
            else:
                # 이동 점프(횟수만큼)
                for _ in range(cnt):
                    pyautogui.press(self.jump_key)
                    time.sleep(0.5)
                return True
        
        elif wp.action == "ladder":
            if self.shift_down:
                self._ensure_key(self.attack_key, 'shift_down', False)

            # self._ensure_key('left',  'left_down', False)
            # self._ensure_key('right', 'right_down', False)

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

                    # 목표 y 도달?
                    if target_y is not None and cy <= target_y:

                        # utils.display_message("도착!","도착!")
                        
                        # time.sleep(0.5)
                        success = True
                        break
                    # if cy - target_y > 4 :
                    #     print("떨어짐")
                    #     break


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
        """↓+Jump(Alt)로 아래 플랫폼으로 내려가기 — 공격키/방향키와 충돌 방지"""
        # 공격키/점프키 동시 입력 방지
        pyautogui.keyUp(self.attack_key)
        self.shift_down = False

        # 방향키는 굳이 누른 채일 필요 없음
        if self.left_down:
            pyautogui.keyUp('left');  self.left_down  = False
        if self.right_down:
            pyautogui.keyUp('right'); self.right_down = False

        pyautogui.keyDown('down')
        pyautogui.press(self.jump_key)   # Alt 단발
        time.sleep(0.12)
        pyautogui.keyUp('down')
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

