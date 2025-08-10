import threading
import time
from src.command_book.command_book import CommandBook
from src.constant import route_ptrol
import pyautogui
from src.common import config, utils,settings
# from src.routine.routine import Routine

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
        config.bot = self

        self.command_book = None            # CommandBook instance
        # config.routine = Routine()

        self.ready = False
        self.thread = threading.Thread(target=self._main)
        self.thread.daemon = True
        self.found_monster = False
        self.keydown = ''
        self.shift_down = self.left_down = self.up_down = self.right_down = self.z_down = False
        self.route = RoutePatrol(route_ptrol)   

        self._last_x = None
        self._stuck_since = None
        self._jump_tries = 0
        self._max_jump_tries = 1           # 점프 재시도 횟수 (원하면 1로 줄여도 됨)

        # 튜닝 파라미터
        self._stuck_eps_px = 1.0           # 이 픽셀 이하로만 움직이면 "안 움직임"으로 간주
        self._stuck_confirm_sec = 0.01     # 이 시간 이상 정체면 막힘 확정
        self._jump_cooldown = 0.01          # 점프 시도 간 최소 간격(스팸 방지)
        self._last_jump_t = 0.0

        self._kb_prev_x = None
        self._kb_last_event_t = 0.0
        self._kb_px = 1.0               # 이 크기 이상 반대로 튀면 '넉백'으로 간주
        self._kb_cooldown = 0.6         # 넉백 감지 후 재트리거 쿨타임
        self._kb_attack_key = 'shift'   # 넉백 시 한번 쓸 공격키('shift' 권장, 'z'로 바꿔도 됨)
        self._kb_ignore_after_jump = 0.25  # 우리가 방금 점프한 직후는 넉백으로 보지 않기
    

    def _tap(self, key, duration=0.06):
        pyautogui.keyDown(key); time.sleep(duration); pyautogui.keyUp(key)

    def _attack_once(self):
        key = self._kb_attack_key
        # 기본공격 z를 계속 누르고 있으니, 순간 스킬(shift) 탭을 추천.
        # z를 계속 유지하면 스킬이 씹히는 경우가 있어서 잠깐 떼고 다시 눌러줌.
        if self.z_down:
            pyautogui.keyUp('z'); self.z_down = False
            time.sleep(0.01)
            self._tap(key, 0.05)
            time.sleep(0.01)
            pyautogui.keyDown('z'); self.z_down = True
        else:
            self._tap(key, 0.05)

    def _probe_knockback_and_attack(self):
        pos = config.player_pos_ab
        if not pos:
            self._kb_prev_x = None
            return False

        x, _ = pos
        moving_right = self.right_down and not self.left_down
        moving_left  = self.left_down and not self.right_down

        # 좌/우로 실제 이동 입력 중이 아니면 패스
        if not (moving_right or moving_left):
            self._kb_prev_x = x
            return False

        if self._kb_prev_x is None:
            self._kb_prev_x = x
            return False

        dx = x - self._kb_prev_x
        self._kb_prev_x = x
        now = time.time()

        # # 방금 우리가 점프한 직후의 x변동은 무시
        if (now - self._last_jump_t) < self._kb_ignore_after_jump:
            return False
        # 오른쪽 진행 중인데 x가 감소(=왼쪽으로 튐)
        if moving_right and dx + 1 <= -self._kb_px and (now - self._kb_last_event_t) >= self._kb_cooldown:
            print(f"[KB] knockback while RIGHT (dx={dx:.1f}) → attack once")
            self._attack_once()
            self._kb_last_event_t = now
            return True

        # 왼쪽 진행 중인데 x가 증가(=오른쪽으로 튐)
        if moving_left and dx -1 >= self._kb_px and (now - self._kb_last_event_t) >= self._kb_cooldown:
            print(f"[KB] knockback while LEFT (dx={dx:.1f}) → attack once")
            self._attack_once()
            self._kb_last_event_t = now
            return True

        return False



    def _probe_stuck_and_jump(self):
        # 전투 중(shift_down)엔 점프하지 않음
        if self.shift_down:
            self._stuck_since = None
            self._last_x = None
            self._jump_tries = 0
            return False

        pos = config.player_pos_ab
        if not pos:
            return False

        x, _ = pos

        # 좌우 키를 실제로 누르고 있을 때만 체크
        # if not (self.left_down or self.right_down):
        #     self._stuck_since = None
        #     self._last_x = x
        #     self._jump_tries = 0
        #     return False

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
            if (now - self._stuck_since) >= self._stuck_confirm_sec and (now - self._last_jump_t) >= self._jump_cooldown:
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
                self.shift_down = True
                pyautogui.keyUp("z")
                pyautogui.keyDown("shift")
            else:
                self.shift_down = False
                pyautogui.keyUp("shift")
                pyautogui.keyDown("z")
            
                wp = self.route.current_wp()
                target_x, target_y, act = wp["x"], wp["y"], wp["action"]
                _, cur_y = config.player_pos_ab

                if target_y > cur_y + 6:          # 목표 y 가 내 y 보다 충분히 더 큼(=아래)
                    self.drop_down()
                    time.sleep(0.25)              # 낙하 안정화
                    continue                      # 다음 loop 에서 다시 판단

                elif target_y + 6 < cur_y :  
                    self.sync_waypoint_to_y()

                if self.reached(wp):
                    self.do_action(wp)
                    self.route.advance()
            
                else:
                    self.move_toward(target_x, act)
                    self._probe_knockback_and_attack()   # ← 추가
                    self._probe_stuck_and_jump()
                time.sleep(0.15)
                


    def move_toward(self, target_x, action):
        """목표 x 로 이동. action='ladder' 면 1픽셀, 나머지는 5픽셀 오차로 멈춘다"""
        cur_x = config.player_pos_ab[0]
        dx = target_x - cur_x
        
        # print(f"[MOVE] cur_x={cur_x:3}  target_x={target_x:3}  dx={dx:+3}")
        thresh = 1 if action == "ladder" else 5   # ★ 차별화
        
        self._ensure_key('z',  'z_down', True)
        
        if dx < -thresh:
            self._ensure_key('left',  'left_down', True)
            config.bot.keydown = 'left'
            if self.right_down:
                self._ensure_key('right',  'right_down', False)
        elif dx > thresh:
            self._ensure_key('right', 'right_down', True)
            config.bot.keydown = 'right'
            if self.left_down:
                self._ensure_key('left',  'left_down', False)

        # ── 오차 범위 안(정지) ───────────────
        else:
            if self.left_down or self.right_down:
                print("  → STOP (x 오차 허용범위)")
            if self.left_down:  self._ensure_key('left',  'left_down', False)
            if self.right_down: self._ensure_key('right',  'right_down', False)


    def sync_waypoint_to_y(self):
        cx, cy = config.player_pos_ab

        best_i = min(
            range(len(self.route.waypoints)),
            key=lambda i: (
                abs(self.route.waypoints[i]["y"] - cy),   # ① y 차
                abs(self.route.waypoints[i]["x"] - cx)    # ② x 차
            )
        )

        if best_i != self.route.index:
            self.route.index = best_i
            print(f"[WP] Y-sync → #{best_i}  cur_y={cy}")
            print(f"[INFO] WP 재동기화(Y 기준) → #{best_i} (x:{cx}, y:{cy})")
    
    def reached(self, wp):
        """웨이포인트에 도달했는지 여부를 반환"""
        cx, cy = config.player_pos_ab
        dx = abs(cx - wp["x"])
        dy = abs(cy - wp["y"])
        hit = False
        if wp["action"] == "ladder":
            # 사다리는 x 정밀도만 중요 (+/-1px)
            tol = 1 if not (self.left_down or self.right_down) else 5
            hit=  dx <= tol
        else:
            # 나머지는 x, y 모두 여유 있게
            hit=  dx <= 6 and dy <= 6
        # print(f"[REACHED?] wp#{self.route.index} "
        #           f"dx={dx:.1f} dy={dy:.1f}  → {hit}")
        return hit
    
    def do_action(self,  wp=None):
        if wp["action"] == "jump":
            count = wp.get("count", 1) if wp else 1
            
            for _ in range(count):
                pyautogui.press("alt")
                time.sleep(0.5)  
            return True

        if wp["action"] == "ladder":
            if self.shift_down:
                self._ensure_key('shift',  'shift_down', False)
                return
            if self.left_down:  
                self._ensure_key('left',  'left_down', True)
            else:
                self._ensure_key('right',  'right_down', True)
            
            pyautogui.press("alt")        # 사다리 붙기용 점프
            self._ensure_key('up',  'up_down', True)

            try:
                target_y  = wp.get("end_y") if wp else None
                start_t   = time.time()
                max_wait  = 2.5           # ← 전역 타임아웃(초)
                prev_cy   = None
                stall_t   = time.time()

                while True:
                    pos = config.player_pos_ab
                    if not pos:
                        time.sleep(0.05)
                        continue

                    _, cy = pos

                    # ── ① 목표 y 도달 ─────────────────────────
                    if target_y is not None and cy <= target_y :
                        return True

                    # ── ② y 값이 변했는가? (정체 감지) ───────
                    if prev_cy is None or abs(cy - prev_cy) > 1:
                        prev_cy = cy
                        stall_t = time.time()        # 움직임이 있으면 리셋

                    # 0.6 s 동안 y 변화가 없으면 실패로 간주
                    if time.time() - stall_t > 0.6:
                        # print("[WARN] 사다리 정체 → 중단")
                        return False

                    # ── ③ 전역 타임아웃 ──────────────────────
                    if time.time() - start_t > max_wait:
                        # print("[WARN] 사다리 타임아웃 → 중단")
                        # print("    ↳ time-out while climbing")
                        return False

                    time.sleep(0.05)

            finally:
                self._ensure_key('up',  'up_down', False)
                self._ensure_key('left',  'left_down', False)
                self._ensure_key('right',  'right_down', False)
    def drop_down(self):
        """↓+Alt 로 아래 플랫폼으로 내려가기"""
        pyautogui.keyDown('down')
        pyautogui.press('alt')       # 점프키 → 드랍
        time.sleep(0.12)             # 짧게 눌렀다 떼기
        pyautogui.keyUp('down')

    def _release_all_keys(self):
        for k in ('shift', 'left', 'right', 'up', 'down', 'z'):
            pyautogui.keyUp(k)
        self.shift_down = self.left_down = self.right_down = self.up_down = False     

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


                
        