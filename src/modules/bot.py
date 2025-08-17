import math
import threading
import time
from src.command_book.command_book import CommandBook
from src.constant import route_ptrol
import pyautogui
from src.common import config, utils,settings
# from src.routine.routine import Routine

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

        self.command_book = None            # CommandBook instance

        self.ready = False
        self.thread = threading.Thread(target=self._main)
        self.thread.daemon = True
        self.found_monster = False
        self.prev_direction = ''
        self.shift_down = self.left_down = self.up_down = self.right_down = self.z_down = False

        self._last_x = None
        self._stuck_since = None
        self._jump_tries = 0
        self._max_jump_tries = 1           # 점프 재시도 횟수 (원하면 1로 줄여도 됨)

        # 튜닝 파라미터
        self._stuck_eps_px = 1.0           # 이 픽셀 이하로만 움직이면 "안 움직임"으로 간주
        self._stuck_confirm_sec = 0.15     # 이 시간 이상 정체면 막힘 확정
        self._jump_cooldown = 0.01          # 점프 시도 간 최소 간격(스팸 방지)
        # self._last_jump_t = 0.0

        self.is_climbing = False          # 등반 중(부착~해제)
        self._no_attack_until = 0.0       # 이 시간 전까지는 공격 금지(그레이스)
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
        self._fm_use_jump = True      # True면 점프-대시(Alt+방향), False면 걷기만
        self._fm_last_exec_t = 0.0
    
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
                self._ensure_key('shift', 'shift_down', False)
                self._ensure_key('left',  'left_down',  False)
                self._ensure_key('right', 'right_down', False)

                # 탈출 방향 선택: 보던 반대 방향 우선(벽에 붙은 경우 유리)
                if self.prev_direction == 'right':
                    escape_dir = 'left'
                elif self.prev_direction == 'left':
                    escape_dir = 'right'
                else:
                    escape_dir = 'right'   # 기본값

                # 대시 실행
                if self._fm_use_jump:
                    # 점프-대시(장애물 넘기 좋음)
                    self._ensure_key(escape_dir, f'{escape_dir}_down', True)
                    pyautogui.keyDown('alt')
                    time.sleep(self._fm_press_sec)
                    self._ensure_key(escape_dir, f'{escape_dir}_down', False)
                    pyautogui.keyUp('alt')
                else:
                    # 걷기-대시(수평만)
                    self._ensure_key(escape_dir, f'{escape_dir}_down', True)
                    time.sleep(self._fm_press_sec)
                    self._ensure_key(escape_dir, f'{escape_dir}_down', False)

                # 상태 업데이트
                self._fm_last_exec_t = now
                self._fm_stuck_since = None
                self._fm_tries += 1
                if self._fm_tries >= self._fm_max_tries:
                    # 반복 탈출 실패 시 완전 리셋(원하면 여기서 방향 전환 등 추가)
                    self._fm_tries = 0

                # 원래 바라보던 방향 복구(선택)
                if self.prev_direction and self.prev_direction != escape_dir:
                    self._ensure_key(self.prev_direction, f'{self.prev_direction}_down', True)
                    # 너무 오래 누르지 않도록 살짝만 눌렀다가 떼어도 됨
                    time.sleep(0.05)
                    self._ensure_key(self.prev_direction, f'{self.prev_direction}_down', False)

                return True
            # 아직 정체 시간이 부족 → 대기
            return False

        # 정상 이동 중이면 리셋
        self._fm_reset()
        return False


    
    def _refresh_can_attack(self, act, dx_abs):
        """
        dx_abs: |target_x - cur_x|
        사다리 접근/부착 구간이거나, Up 홀드(등반중)이거나,
        공격 금지 그레이스가 남아있을 때만 공격 금지.
        """
        now = time.time()

        NEAR_LADDER_WIN = 6   # PREP_WIN 과 맞춤
        near_ladder = (act == "ladder" and dx_abs <= NEAR_LADDER_WIN)

        ban = self.up_down or near_ladder or (now < self._no_attack_until)
        self.can_attack = not ban
    
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
        self._ensure_key('shift', 'shift_down', True)
        time.sleep(0.01)
        self._ensure_key('shift', 'shift_down', False)
        self._ensure_key(last_direction, f'{last_direction}_down', True)

             

    def _new_direction(self, new_direction):
        self._ensure_key('z',  'z_down', False)
        self._ensure_key(new_direction,  f'{new_direction}_down', True)
        
        if self.prev_direction and self.prev_direction != new_direction:
            self._ensure_key(self.prev_direction,  f'{self.prev_direction}_down', False)
        self.prev_direction = new_direction
        self._ensure_key('z',  'z_down', True)


    


    def _probe_stuck_and_jump(self):
        # 전투 중(shift_down)엔 점프하지 않음
        if self.shift_down or self.up_down:
            self._stuck_since = None
            self._last_x = None
            self._jump_tries = 0
            return False

        pos = config.player_pos_ab
        if not pos:
            return False

        x, _ = pos

        # 첫 측정
        if self._last_x is None:
            self._last_x = x
            return False

        dx = abs(x - self._last_x)
        self._last_x = x
        now = time.time()

        if dx < self._stuck_eps_px:
            # 정체 시작/유지
            if self._stuck_since is None:
                self._stuck_since = now
                return False

            # 정체가 충분히 이어졌고, 쿨다운도 지났으면 점프
            if (now - self._stuck_since) >= self._stuck_confirm_sec :
                pyautogui.press('alt')     # ← 점프!
                self._last_jump_t = now
                self._jump_tries += 1

                # 여러 번 연속 시도 후엔 상태 리셋(원하면 방향전환 로직 붙여도 됨)
                if self._jump_tries >= self._max_jump_tries:
                    self._stuck_since = None
                    self._jump_tries = 0
                return True
        else:
            # 정상 이동 중이면 상태 리셋
            self._stuck_since = None
            self._jump_tries = 0
        return False
    
    def start(self):
        print('\n[~] Started main bot loop')
        self.thread.start()

    def aa(self):
        print("")
        #여기부터
                # if self.prev_char_pos and config.player_pos_ab:
                #     if math.hypot(config.player_pos_ab[0]-self.prev_char_pos[0],
                #                 config.player_pos_ab[1]-self.prev_char_pos[1]) < 3:
                #         self.stuck_attack_cnt += 1
                #     else:
                #         self.stuck_attack_cnt = 1
                # else:
                #     self.stuck_attack_cnt = 1
                

                # self.prev_char_pos = config.player_pos_ab

                # if self.stuck_attack_cnt >= 3:
                #     print("[INFO] 같은 자리 3회 공격 → 강제 이동")
                #     self._release_all_keys()
                #     # (2) 0.4초간 오른쪽으로 대시
                #     self._ensure_key('right',  'right_down', True)
                #     pyautogui.keyDown('alt'); time.sleep(0.4)
                #     self._ensure_key('right',  'right_down', False)
                #     pyautogui.keyUp('alt')
                #     self._ensure_key('z',  'z_down', False)
                #     self.sync_waypoint_to_y()
                #     # self.reselect_waypoint()
                #     self.stuck_attack_cnt = 0
                #     # ↑ 강제 이동 결정 후 곧바로 다음 루프
                #     time.sleep(0.1)
                #     continue     
                # 여기부터 여기까지 확인
                #                
    def _nudge_toward(self, target_x, step_ms=0.02):
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

    def _main(self):
        self.ready = True
        
        while True:
            if config.enabled is False:
                time.sleep(0.001)
                continue
                
            if self.found_monster :
                self._ensure_key('z', 'z_down', False); 
                self._ensure_key('shift', 'shift_down', True); 

                if self.prev_char_pos and config.player_pos_ab:
                    dif = math.hypot(config.player_pos_ab[0]-self.prev_char_pos[0],
                                config.player_pos_ab[1]-self.prev_char_pos[1])
                    if dif < 3:
                        self.stuck_attack_cnt += 1
                    else:
                        self.stuck_attack_cnt = 1
                else:
                    self.stuck_attack_cnt = 1
                
                self.prev_char_pos = config.player_pos_ab
                
                if self.stuck_attack_cnt >= 10:
                    print("[INFO] 같은 자리 10회 공격 → 강제 이동")
                    self.release_all_keys()
                    self.sync_direction()
                    pyautogui.press('alt')
                    self.sync_waypoint_to_y()
                    self.stuck_attack_cnt = 0
                    time.sleep(0.1)
                    continue     
                time.sleep(0.1)
                    
            else:
                self.stuck_attack_cnt = 0
                self._ensure_key('shift', 'shift_down', False); 
                # self._ensure_key('z', 'z_down', True); 
                
                wp = config.routine.current_wp()
                target_x, target_y, act = wp.x, wp.y, wp.action
                cur_x, cur_y = config.player_pos_ab

                dx = target_x - cur_x
                dy = target_y - cur_y
                dx_abs = abs(dx)
                dy_abs = abs(dy)

                # 공격 가능 여부는 "거리"로 결정
                self._refresh_can_attack(act, dx_abs)

                if  target_y > cur_y + 6 and  cur_y - target_y > -35  :
                    print("?")
                    self.drop_down()
                    time.sleep(0.25)              # 낙하 안정화
                    continue                      # 다음 loop 에서 다시 판단
                
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
                    if self.do_action(wp):
                        self.prev_action = wp.action
                        print(f'self.prev_action : {self.prev_action}')
                        config.routine.advance()
                else:
                    self.move_toward(target_x, act)
                    triggered = self._probe_stuck_and_jump()
                    # if not triggered:
                    self._probe_stuck_and_force_move()
            
                    self._weave_attack()

                time.sleep(0.15)
                

    def move_toward(self, target_x, action):

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
                self._nudge_toward(target_x, step_ms=0.02)

            # 3) 충분히 가까우면 바로 부착(Up+Jump) 실행
            if abs(dx) <= ATTACH_WIN:
                print("if abs(dx) <= ATTACH_WIN:")
                self._ensure_key('up', 'up_down', True)
                time.sleep(0.02)
                pyautogui.press('alt')         
                self.is_climbing = True
                self._no_attack_until = time.time() + 0.30
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
                print("aa")
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
            print(f"[INFO] WP 재동기화(Y 기준) → #{best_i+1} (x:{cx}, y:{cy})")
    
    def reached(self, wp):
        """웨이포인트에 도달했는지 여부를 반환"""
        cx, cy = config.player_pos_ab
        dx = abs(cx - wp.x)
        dy = abs(cy - wp.y)
        hit = False

        if wp.action == "ladder":
            # 사다리는 x 정밀도만 중요 (+/-1px)
            tol = 0  if not (self.left_down or self.right_down) else 5
            
            hit=  dx <= tol
        elif wp.action == "jump":
            in_place = getattr(wp, "in_place", False)
            # move_toward()의 STOP_TOL과 맞춰 2px로 완화
            tol = 0 if in_place else (2 if self.prev_action == 'ladder' else 5)
            print(f'tol : {tol}')
            
            return dx <= tol
        else:
            hit=  dx <= 5 and dy <= 5
        
        return hit
    
    def do_action(self,  wp=None):
        if wp.action == "jump":
            in_place = getattr(wp, "in_place", False)
            cnt = wp.count
            print(f'in_place : {in_place}')
            if in_place:
                print(f'cnt : {cnt}')
                
                # 움직임 키 완전히 해제하고 제자리 점프만
                self._ensure_key('left',  'left_down',  False)
                self._ensure_key('right', 'right_down', False)
                # 공격/기타 키도 필요하면 해제
                self._ensure_key('shift', 'shift_down', False)
                # 약간의 안정화
                time.sleep(0.5)

                for _ in range(cnt):
                    pyautogui.press('alt')
                    time.sleep(0.5)
                print("RETURN")
                return True
            else:
                # 이동 점프(횟수만큼)
                for _ in range(cnt):
                    pyautogui.press('alt')
                    time.sleep(0.5)
                return True
        
        if wp.action == "ladder":
            if self.shift_down:
                self._ensure_key('shift', 'shift_down', False)

            self._ensure_key('left',  'left_down', False)
            self._ensure_key('right', 'right_down', False)

            # 0) x 미세 정렬(안전장치)
            success = False
            target_x = wp.x
            while True:
                cx, _ = config.player_pos_ab
                if abs(cx - target_x) <= 1:
                    break
                self._nudge_toward(target_x, step_ms=0.02)
                time.sleep(0.01)

            # 1) 즉시 부착 시도 (Up+Jump)
            print("1) 즉시 부착 시도 (Up+Jump)")
            pyautogui.press("alt")   # 붙기 점프
            self._ensure_key('up', 'up_down', True)
            time.sleep(0.02)
            self.is_climbing = True
            self._no_attack_until = time.time() + 0.30
            try:
                target_y  = wp.end_y if wp else None
                prev_cy   = None
                stall_t   = time.time()

                while True:
                    pos = config.player_pos_ab
                    
                    if not pos:
                        time.sleep(0.03)
                        continue

                    _, cy = pos

                    # 목표 y 도달?
                    if target_y is not None and cy <= target_y:
                        time.sleep(0.5)
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
                        return False

                    time.sleep(0.03)
            finally:
                time.sleep(0.35)
                self._ensure_key('up',  'up_down', False)
                self.is_climbing = False
                self._no_attack_until = time.time() + 0.25

                time.sleep(0.25)
                if self.left_down == False and self.right_down == False and self.prev_direction != '':
                        print(f'self.prev_direction : {self.prev_direction}')
                        if self.prev_direction =='right':
                            self.right_down = True
                            pyautogui.press('right') 
                        else:
                            self.left_down = True
                            pyautogui.press('left') 
            return success

        return True
    def drop_down(self):
        """↓+Alt 로 아래 플랫폼으로 내려가기"""
        pyautogui.keyDown('down')
        pyautogui.press('alt')       # 점프키 → 드랍
        time.sleep(0.12)             # 짧게 눌렀다 떼기
        pyautogui.keyUp('down')

    def release_all_keys(self):
        for k in ('shift', 'left', 'right', 'up', 'down', 'z'):
            pyautogui.keyUp(k)
        self.shift_down = self.left_down = self.up_down = self.right_down = self.z_down = False

    def _ensure_key(self, key, flag_attr, value):
        if value:  
            pyautogui.keyDown(key)
            setattr(self, flag_attr, True)
        else:
            pyautogui.keyUp(key)
            setattr(self, flag_attr, False)

    def load_commands(self, file):
        try:
            self.command_book = CommandBook(file)
            # config.gui.settings.update_class_binding()
        except ValueError:
            print("file to load_commands")
            pass


                
        