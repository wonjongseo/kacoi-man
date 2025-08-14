
import json
import os
import threading
import time
from src.modules.bot import Bot
from src.modules.capture import Capture
from src.modules.notifier import Notifier
from src.modules.listener import Listener
from src.gui.interfaces import Tab,LabelFrame
import tkinter as tk
from tkinter import  ttk, filedialog, messagebox
import src.datas.setting_data as sd
from  src.common  import config

class Settings(Tab):

    def _create_monster_feild(self,row_index):
        # 몬스터 폴더
        frm_mon = ttk.LabelFrame(self, text="몬스터 폴더")
        frm_mon.grid(row=row_index, column=0, sticky="ew", padx=4, pady= (0,10))
        frm_mon.columnconfigure(0, weight=1)
        ttk.Entry(frm_mon, textvariable=self.var_monster_dir)\
            .grid(row=0, column=0, sticky="ew", padx=(8,4), pady=8)
        ttk.Button(frm_mon, text="찾아보기…",
                   command=lambda: self._browse_dir(self.var_monster_dir))\
            .grid(row=0, column=1, sticky="ew", padx=(0,8), pady=8)
    def _create_potion_feild(self,row_index):
        # 포션 임계치
        frm_potion = ttk.LabelFrame(self, text="포션 사용 임계치 (%)")
        frm_potion.grid(row=row_index, column=0, sticky="ew", padx=4, pady=(0,10))
        # 가로 칼럼 늘리기 (퍼센트 + 키 2쌍을 위해)
        frm_potion.columnconfigure(1, weight=1)
        frm_potion.columnconfigure(4, weight=1)

        ttk.Label(frm_potion, text="최소 HP 물약 사용 %")\
            .grid(row=0, column=0, sticky="w", padx=8, pady=(8,4))
        ttk.Spinbox(frm_potion, from_=0, to=100, textvariable=self.var_hp_pct, width=6, justify="right")\
            .grid(row=0, column=1, sticky="w", pady=(8,4))

        # HP key  ← 추가
        ttk.Label(frm_potion, text="HP 키").grid(row=0, column=3, sticky="e", padx=(16,4), pady=(8,4))
        ttk.Entry(frm_potion, textvariable=self.var_hp_key, width=10)\
            .grid(row=0, column=4, sticky="w", padx=(0,8), pady=(8,4))


        ttk.Label(frm_potion, text="최소 MP 물약 사용 %")\
            .grid(row=1, column=0, sticky="w", padx=8, pady=(0,8))
        ttk.Spinbox(frm_potion, from_=0, to=100, textvariable=self.var_mp_pct, width=6, justify="right")\
            .grid(row=1, column=1, sticky="w", pady=(0,8))

        
        # MP key  ← 추가
        ttk.Label(frm_potion, text="MP 키").grid(row=1, column=3, sticky="e", padx=(16,4), pady=(0,8))
        ttk.Entry(frm_potion, textvariable=self.var_mp_key, width=10)\
            .grid(row=1, column=4, sticky="w", padx=(0,8), pady=(0,8))
    
    def _create_attack_range_feild(self,row_index):
        # 공격 사거리(px)
        frm_range = ttk.LabelFrame(self, text="공격 사거리 (px)")
        frm_range.grid(row=row_index, column=0, sticky="ew", padx=4, pady=(0,10))
        for c in (1,3): frm_range.columnconfigure(c, weight=1)
        ttk.Label(frm_range, text="전방").grid(row=0, column=0, sticky="w", padx=8, pady=(8,4))
        ttk.Spinbox(frm_range, from_=0, to=5000, textvariable=self.var_rng_front, width=7, justify="right")\
            .grid(row=0, column=1, sticky="w", pady=(8,4))
        ttk.Label(frm_range, text="후방").grid(row=0, column=2, sticky="w", padx=(16,8), pady=(8,4))
        ttk.Spinbox(frm_range, from_=0, to=5000, textvariable=self.var_rng_back, width=7, justify="right")\
            .grid(row=0, column=3, sticky="w", pady=(8,4))
        ttk.Label(frm_range, text="위").grid(row=1, column=0, sticky="w", padx=8, pady=(0,8))
        ttk.Spinbox(frm_range, from_=0, to=5000, textvariable=self.var_rng_up, width=7, justify="right")\
            .grid(row=1, column=1, sticky="w", pady=(0,8))
        ttk.Label(frm_range, text="아래").grid(row=1, column=2, sticky="w", padx=(16,8), pady=(0,8))
        ttk.Spinbox(frm_range, from_=0, to=5000, textvariable=self.var_rng_down, width=7, justify="right")\
            .grid(row=1, column=3, sticky="w", pady=(0,8))
    
    def _create_template_images_feild(self, row_index):
        # 템플레이트 이미지 (PNG)
        frm_tmpl = ttk.LabelFrame(self, text="게임 설정 템플레이트 이미지 (PNG)")
        frm_tmpl.grid(row=row_index, column=0, sticky="ew", padx=4, pady=(0,10))
        frm_tmpl.columnconfigure(1, weight=1)
        frm_tmpl.columnconfigure(4, weight=1)

        # -- 미니맵 --
        ttk.Label(frm_tmpl, text="-- 미니맵 --").grid(row=0, column=0, columnspan=5, sticky="w", padx=8, pady=(8,4))

        ttk.Label(frm_tmpl, text="상단-왼쪽 모서리").grid(row=1, column=0, sticky="w", padx=8)
        ttk.Entry(frm_tmpl, textvariable=self.var_mm_tl)\
            .grid(row=1, column=1, sticky="ew", padx=(0,4))
        ttk.Button(frm_tmpl, text="찾기", command=lambda: self._browse_png(self.var_mm_tl))\
            .grid(row=1, column=2, padx=(0,8))

        ttk.Label(frm_tmpl, text="하단-오른쪽 모서리").grid(row=1, column=3, sticky="w", padx=8)
        ttk.Entry(frm_tmpl, textvariable=self.var_mm_br)\
            .grid(row=1, column=4, sticky="ew", padx=(0,4))
        ttk.Button(frm_tmpl, text="찾기", command=lambda: self._browse_png(self.var_mm_br))\
            .grid(row=1, column=5, padx=(0,8))

        ttk.Label(frm_tmpl, text="내 캐릭터 아이콘").grid(row=2, column=0, sticky="w", padx=8, pady=(4,0))
        ttk.Entry(frm_tmpl, textvariable=self.var_mm_me)\
            .grid(row=2, column=1, sticky="ew", padx=(0,4), pady=(4,0))
        ttk.Button(frm_tmpl, text="찾기", command=lambda: self._browse_png(self.var_mm_me))\
            .grid(row=2, column=2, padx=(0,8), pady=(4,0))

        ttk.Label(frm_tmpl, text="다른 캐릭터 아이콘").grid(row=2, column=3, sticky="w", padx=8, pady=(4,0))
        ttk.Entry(frm_tmpl, textvariable=self.var_mm_other)\
            .grid(row=2, column=4, sticky="ew", padx=(0,4), pady=(4,0))
        ttk.Button(frm_tmpl, text="찾기", command=lambda: self._browse_png(self.var_mm_other))\
            .grid(row=2, column=5, padx=(0,8), pady=(4,0))

        # -- 캐릭터 --
        ttk.Label(frm_tmpl, text="-- 캐릭터 --").grid(row=3, column=0, columnspan=5, sticky="w", padx=8, pady=(10,4))

        ttk.Label(frm_tmpl, text="HP 바 이미지").grid(row=4, column=0, sticky="w", padx=8)
        ttk.Entry(frm_tmpl, textvariable=self.var_chr_hp)\
            .grid(row=4, column=1, sticky="ew", padx=(0,4))
        ttk.Button(frm_tmpl, text="찾기", command=lambda: self._browse_png(self.var_chr_hp))\
            .grid(row=4, column=2, padx=(0,8))

        ttk.Label(frm_tmpl, text="MP 바 이미지").grid(row=4, column=3, sticky="w", padx=8)
        ttk.Entry(frm_tmpl, textvariable=self.var_chr_mp)\
            .grid(row=4, column=4, sticky="ew", padx=(0,4))
        ttk.Button(frm_tmpl, text="찾기", command=lambda: self._browse_png(self.var_chr_mp))\
            .grid(row=4, column=5, padx=(0,8))

        ttk.Label(frm_tmpl, text="캐릭터 이름 이미지").grid(row=5, column=0, sticky="w", padx=8, pady=(4,8))
        ttk.Entry(frm_tmpl, textvariable=self.var_chr_name)\
            .grid(row=5, column=1, sticky="ew", padx=(0,4), pady=(4,8))
        ttk.Button(frm_tmpl, text="찾기", command=lambda: self._browse_png(self.var_chr_name))\
            .grid(row=5, column=2, padx=(0,8), pady=(4,8))
        
        # -- 기타 --
        ttk.Label(frm_tmpl, text="-- 기타 --").grid(row=6, column=0, columnspan=5,
                                                    sticky="w", padx=8, pady=(10,4))

        ttk.Label(frm_tmpl, text="부활메세지 이미지").grid(row=7, column=0, sticky="w", padx=8)
        ttk.Entry(frm_tmpl, textvariable=self.var_misc_revive)\
            .grid(row=7, column=1, sticky="ew", padx=(0,4))
        ttk.Button(frm_tmpl, text="찾기",
                command=lambda: self._browse_png(self.var_misc_revive))\
            .grid(row=7, column=2, padx=(0,8))
        
    
    def _create_buff_feild(self, row_index) :
        # ── 버프 ── (포션 사용 임계치 바로 아래)
        frm_buff = ttk.LabelFrame(self, text="버프")
        frm_buff.grid(row=row_index, column=0, sticky="ew", padx=4, pady=(0,10))
        frm_buff.columnconfigure(1, weight=1)

        ttk.Label(frm_buff, text="버프 쿨타임(초)").grid(row=0, column=0, sticky="w", padx=8, pady=(8,4))
        ttk.Spinbox(frm_buff, from_=0, to=36000, textvariable=self.var_buff_cooldown,
                    width=8, justify="right").grid(row=0, column=1, sticky="w", pady=(8,4))

        ttk.Label(frm_buff, text="버프 사용 키").grid(row=1, column=0, sticky="w", padx=8, pady=(0,8))
        ttk.Entry(frm_buff, textvariable=self.var_buff_key)\
            .grid(row=1, column=1, sticky="ew", pady=(0,8))

    def __init__(self, parent, **kwargs):
        super().__init__(parent, "Settings" , **kwargs)

        self.columnconfigure(0, weight=1)
        self.columnconfigure(3, weight=1)

        # ===== Vars =====
        self.var_monster_dir = tk.StringVar()
        self.var_hp_pct = tk.IntVar(value=50)
        self.var_hp_key = tk.StringVar(value="del")
        self.var_mp_pct = tk.IntVar(value=50)
        self.var_mp_key = tk.StringVar(value="end")

        # 공격 사거리(px)
        self.var_rng_front = tk.IntVar(value=220)
        self.var_rng_back  = tk.IntVar(value=0)
        self.var_rng_up    = tk.IntVar(value=50)
        self.var_rng_down  = tk.IntVar(value=50)

        # 템플레이트(이미지 경로)
        self.var_mm_tl   = tk.StringVar()  # minimap top-left
        self.var_mm_br   = tk.StringVar()  # minimap bottom-right
        self.var_mm_me   = tk.StringVar()  # minimap player
        self.var_mm_other= tk.StringVar()  # minimap other
        self.var_chr_hp  = tk.StringVar()  # character HP bar
        self.var_chr_mp  = tk.StringVar()  # character MP bar
        self.var_chr_name= tk.StringVar()  # character name
        self.var_misc_revive = tk.StringVar()  

        self.var_buff_cooldown = tk.IntVar(value=0)   # 초 단위
        self.var_buff_key = tk.StringVar(value="")    # 예: F1, Q, shift+a



        # ===== Layout =====
        self.columnconfigure(0, weight=1)

        self._create_attack_range_feild(2)
        
        self._create_template_images_feild(0)

        self._create_monster_feild(1)

        self._create_potion_feild(3)
        
        self._create_buff_feild(4)

        # 하단 버튼
        btns = ttk.Frame(self)
        btns.grid(row=5, column=0, sticky="ew", pady=(4,0))
        btns.columnconfigure(0, weight=1)
        ttk.Button(btns, text="✅ 적용", command=self._apply).grid(row=0, column=1, padx=4)
        ttk.Button(btns, text="💾 저장", command=self._save_json).grid(row=0, column=2, padx=4)
        ttk.Button(btns, text="📂 불러오기", command=self._load_json).grid(row=0, column=3, padx=4)
        ttk.Button(btns, text="초기화", command=self._reset).grid(row=0, column=4, padx=4)

    def get_config(self) -> sd.SettingsConfig:
        cfg = sd.SettingsConfig(
            monster_dir=self.var_monster_dir.get().strip(),
            hp_pct=sd._clamp_int(self.var_hp_pct.get(), 0, 100, 50),
            mp_pct=sd._clamp_int(self.var_mp_pct.get(), 0, 100, 50),
            hp_key=(self.var_hp_key.get() or "del").strip(),   # ← 추가
            mp_key=(self.var_mp_key.get() or "del").strip(),   # ← 추가
            attack_range=sd.AttackRange(
                front=sd._clamp_int(self.var_rng_front.get(), 0, 5000, 200),
                back=sd._clamp_int(self.var_rng_back.get(), 0, 5000, 120),
                up=sd._clamp_int(self.var_rng_up.get(), 0, 5000, 120),
                down=sd._clamp_int(self.var_rng_down.get(), 0, 5000, 80),
            ),
            templates=sd.Templates(
                minimap=sd.MinimapTemplates(
                    top_left=sd._png_or_empty(self.var_mm_tl.get()),
                    bottom_right=sd._png_or_empty(self.var_mm_br.get()),
                    player=sd._png_or_empty(self.var_mm_me.get()),
                    other=sd._png_or_empty(self.var_mm_other.get()),
                ),
                character=sd.CharacterTemplates(
                    hp_bar=sd._png_or_empty(self.var_chr_hp.get()),
                    mp_bar=sd._png_or_empty(self.var_chr_mp.get()),
                    name=sd._png_or_empty(self.var_chr_name.get()),
                ),
                misc=sd.MiscTemplates(                                # ← 추가
                    revive_message=sd._png_or_empty(self.var_misc_revive.get())
                )
            ),
            buffs=sd.BuffSettings(
                cooldown_sec=sd._clamp_int(self.var_buff_cooldown.get(), 0, 36000, 0),
                key=self.var_buff_key.get().strip(),
            ),
            
        )
        return cfg

    def set_config(self, cfg):
        if isinstance(cfg, dict):
            cfg = sd.SettingsConfig.from_dict(cfg)
        if not isinstance(cfg, sd.SettingsConfig):
            return

        self.var_monster_dir.set(cfg.monster_dir)
        self.var_hp_pct.set(cfg.hp_pct)
        self.var_mp_pct.set(cfg.mp_pct)
        self.var_hp_key.set(getattr(cfg, "hp_key", "del"))  
        self.var_mp_key.set(getattr(cfg, "mp_key", "end"))  
        self.var_rng_front.set(cfg.attack_range.front)
        self.var_rng_back.set(cfg.attack_range.back)
        self.var_rng_up.set(cfg.attack_range.up)
        self.var_rng_down.set(cfg.attack_range.down)

        self.var_mm_tl.set(cfg.templates.minimap.top_left)
        self.var_mm_br.set(cfg.templates.minimap.bottom_right)
        self.var_mm_me.set(cfg.templates.minimap.player)
        self.var_mm_other.set(cfg.templates.minimap.other)

        self.var_chr_hp.set(cfg.templates.character.hp_bar)
        self.var_chr_mp.set(cfg.templates.character.mp_bar)
        self.var_chr_name.set(cfg.templates.character.name)

        self.var_misc_revive.set(getattr(cfg.templates.misc, "revive_message", ""))  # ← 추가

        self.var_buff_cooldown.set(cfg.buffs.cooldown_sec)
        self.var_buff_key.set(cfg.buffs.key)

    def to_json_str(self) -> str:
        return json.dumps(self.get_config().to_dict(), ensure_ascii=False, indent=2)

    # ========= Internals =========
    def _browse_dir(self, var: tk.StringVar):
        path = filedialog.askdirectory(title="폴더 선택")
        if path: var.set(path)

    def _browse_png(self, var: tk.StringVar):
        path = filedialog.askopenfilename(
            title="PNG 선택",
            filetypes=[("PNG files","*.png"),("All files","*.*")]
        )
        if path: var.set(path)

    def _png_or_empty(self, p: str) -> str:
        p = (p or "").strip()
        if not p:
            return ""
        # 확장자 간단 검증
        if os.path.splitext(p)[1].lower() != ".png":
            messagebox.showwarning("확인", f"PNG 파일이 아닐 수 있습니다:\n{p}")
        return p

    def _clamped_pct(self, v):
        try: v = int(v)
        except (TypeError, ValueError): v = 0
        return max(0, min(100, v))

    def _clamped_px(self, v):
        try: v = int(v)
        except (TypeError, ValueError): v = 0
        return max(0, min(5000, v))

    
    def _save_json(self):
        path = filedialog.asksaveasfilename(
            title="설정을 JSON으로 저장",
            defaultextension=".json",
            filetypes=[("JSON files","*.json"),("All files","*.*")]
        )
        if not path: return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.to_json_str())
            messagebox.showinfo("저장 완료", f"저장됨:\n{path}")
        except Exception as e:
            messagebox.showerror("저장 실패", str(e))

    def _load_json(self):
        path = filedialog.askopenfilename(
            title="설정 JSON 불러오기",
            filetypes=[("JSON files","*.json"),("All files","*.*")]
        )
        if not path: return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("JSON 최상위는 객체여야 합니다.")
            self.set_config(sd.SettingsConfig.from_dict(data))
            messagebox.showinfo("불러오기/적용 완료", "설정을 적용했습니다.")
            self._apply(show_msg=False)
        except Exception as e:
            messagebox.showerror("불러오기 실패", str(e))
    def _reset(self):
        self.var_monster_dir.set("")
        
        self.var_hp_pct.set(50)
        self.var_mp_pct.set(50)
        self.var_hp_key.set("")
        self.var_mp_key.set("") 
        self.var_rng_front.set(200)
        self.var_rng_back.set(120)
        self.var_rng_up.set(120)
        self.var_rng_down.set(80)
        self.var_misc_revive.set("")

        self.var_buff_cooldown.set(0)
        self.var_buff_key.set("")
        
        for v in (self.var_mm_tl, self.var_mm_br, self.var_mm_me, self.var_mm_other,
                  self.var_chr_hp, self.var_chr_mp, self.var_chr_name):
            v.set("")


    
    def _apply(self, show_msg = True):
        cfg = self.get_config()
        
        if cfg.monster_dir == "":
            messagebox.showwarning("확인", "몬스터 폴더를 선택하세요.")
            return
        elif cfg.templates.character.name == "":
            messagebox.showwarning("확인", "캐릭터(이름) 이미지를 선택하세요.")
            return
        if show_msg:
            messagebox.showinfo("적용됨", "설정이 적용되었습니다.")
        config.setting_data = cfg
        config.gui.monitor.refresh_routine()
        config.gui.monitor.refresh_labels()
        self.start_bot()
    
    def start_bot(self):
        threading.Thread(target=self._start_modules_thread, daemon=True).start()

    def _start_modules_thread(self):
        try:
            # 인스턴스 생성 + 전역 등록
            config.bot = Bot()
            config.capture = Capture()         # ← 주입 안 함
            config.notifier = Notifier()
            config.listener = Listener()

            # 순서대로 시작 + 준비 대기 (백그라운드에서만 sleep)
            config.capture.start()
            if not self._wait(lambda: config.capture.ready, 10):  # 타임아웃 권장
                return self._fail("Capture가 준비되지 않습니다.")

            config.bot.start()
            if not self._wait(lambda: config.bot.ready, 5):
                return self._fail("Bot이 준비되지 않습니다.")

            config.listener.start()
            if not self._wait(lambda: config.listener.ready, 5):
                return self._fail("Listener가 준비되지 않습니다.")

            config.notifier.start()
            if not self._wait(lambda: config.notifier.ready, 5):
                return self._fail("Notifier가 준비되지 않습니다.")

            # 메인스레드로 UI 알림
            self.after(0, lambda: messagebox.showinfo("시작", "모듈이 모두 준비되었습니다."))

        except Exception as e:
            self.after(0, lambda: messagebox.showerror("시작 실패", str(e)))

    def _wait(self, pred, timeout_s, interval=0.05):
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            if pred(): return True
            time.sleep(interval)
        return False

    def _fail(self, msg):
        self.after(0, lambda: messagebox.showerror("오류", msg))