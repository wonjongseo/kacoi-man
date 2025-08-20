
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
from  src.common  import config, default_value as dv, utils


def add_placeholder(entry, placeholder):
        def on_focus_in(event):
            if entry.get() == placeholder:
                entry.delete(0, tk.END)
                entry.config(foreground='black')

        def on_focus_out(event):
            if not entry.get():
                entry.insert(0, placeholder)
                entry.config(foreground='gray')

        entry.insert(0, placeholder)
        entry.config(foreground='gray')
        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)
        
class Settings(Tab):
    def _create_required_feild(self, row_index):
        frm_required = ttk.LabelFrame(self, text="---필수 항목---")
        frm_required.grid(row=row_index, column=0, sticky="ew", padx=4, pady=(0, 10))

        # --- 한 행에 두 칼럼 배치 ---
        frm_required.columnconfigure(0, weight=1)
        frm_required.columnconfigure(1, weight=1)

        # [Column 1] 몬스터 폴더
        frm_mon = ttk.LabelFrame(frm_required, text="몬스터 폴더")
        frm_mon.grid(row=0, column=0, sticky="ew", padx=(8, 4), pady=8)
        frm_mon.columnconfigure(0, weight=1)
        ttk.Entry(frm_mon, textvariable=self.var_monster_dir)\
            .grid(row=0, column=0, sticky="ew", padx=(8, 4), pady=8)
        ttk.Button(frm_mon, text="찾아보기…",
                command=lambda: self._browse_dir(self.var_monster_dir))\
            .grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=8)

        # [Column 2] 캐릭터 이름 이미지
        frm_chr = ttk.LabelFrame(frm_required, text="캐릭터 이름 이미지 (PNG)")
        frm_chr.grid(row=0, column=1, sticky="ew", padx=(4, 8), pady=8)
        frm_chr.columnconfigure(0, weight=1)
        ttk.Entry(frm_chr, textvariable=self.var_chr_name)\
            .grid(row=0, column=0, sticky="ew", padx=(8, 4), pady=8)
        ttk.Button(frm_chr, text="찾기",
                command=lambda: self._browse_png(self.var_chr_name))\
            .grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=8)

        # [Row 1][Col 0] 점프 키 : 입력란
        frm_jump = ttk.Frame(frm_required)
        frm_jump.grid(row=1, column=0, sticky="ew", padx=(8, 4), pady=(0, 8))
        frm_jump.columnconfigure(1, weight=1)
        ttk.Label(frm_jump, text="점프 키").grid(row=0, column=0, sticky="w", padx=(0, 4))
        entry_jump = ttk.Entry(frm_jump, textvariable=self.var_jump_key)
        entry_jump.grid(row=0, column=1, sticky="ew", padx=(0, 8))

        # [Row 1][Col 1] 공격 키 : 입력란
        frm_attack = ttk.Frame(frm_required)
        frm_attack.grid(row=1, column=1, sticky="ew", padx=(4, 8), pady=(0, 8))
        frm_attack.columnconfigure(1, weight=1)
        ttk.Label(frm_attack, text="공격 키").grid(row=0, column=0, sticky="w", padx=(0, 4))
        entry_attack = ttk.Entry(frm_attack, textvariable=self.var_attack_key)
        entry_attack.grid(row=0, column=1, sticky="ew", padx=(0, 8))
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
        frm_range.grid(row=row_index, column=0, sticky="ew", padx=4)
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
        ttk.Label(frm_tmpl, text="-- 캐릭터 --").grid(row=3, column=0, columnspan=5, sticky="w", padx=8, pady=(10,8))

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
    def _create_buff_feild(self, row_index) :
        # ── 버프 ── (포션 사용 임계치 바로 아래)
        # __init__ 내, 포션/공격사거리 아래 적당한 위치에 배치
        frm_buffs = ttk.LabelFrame(self, text="버프들")
        frm_buffs.grid(row=row_index, column=0, sticky="ew", padx=4, pady=(0,10))
        frm_buffs.columnconfigure(0, weight=1)

        # 헤더 + 리스트 컨테이너
        hdr = ttk.Frame(frm_buffs)
        hdr.grid(row=0, column=0, sticky="ew", padx=8, pady=(8,4))
        ttk.Label(hdr, text="쿨타임(초)", width=10).grid(row=0, column=0, sticky="w")
        ttk.Label(hdr, text="사용 키",   width=12).grid(row=0, column=1, sticky="w")

        self.frm_buff_list = ttk.Frame(frm_buffs)
        self.frm_buff_list.grid(row=1, column=0, sticky="ew", padx=8)
        self.frm_buff_list.columnconfigure(0, weight=0)
        self.frm_buff_list.columnconfigure(1, weight=1)

        # + 추가 버튼
        self.add_buff_btn = ttk.Button(frm_buffs, text="＋ 버프 추가", command=self._add_buff_row)
        self.add_buff_btn.grid(row=2, column=0, sticky="e", padx=8, pady=(6,8))

        # 버프 행들을 들고 있을 리스트
    def _add_buff_row(self, model: sd.BuffSettings | None = None):
        row = _BuffRow(self.frm_buff_list, self._remove_buff_row)
        if model: row.from_model(model)
        self._buff_rows.append(row)
        self._reflow_buff_rows()

        if len(self._buff_rows) > 4:
            self.add_buff_btn.grid_remove()
    def _remove_buff_row(self, row: "_BuffRow"):
        try:
            self._buff_rows.remove(row)
            if len(self._buff_rows) < 5:
                self.add_buff_btn.grid()
        except ValueError:
            pass
        row.destroy()
        self._reflow_buff_rows()
    def _reflow_buff_rows(self):
        # 현재 행들 다시 grid
        for idx, r in enumerate(self._buff_rows):
            r.grid(row=idx)
    def __init__(self, parent, **kwargs):
        super().__init__(parent, "Settings" , **kwargs)

        
        self.columnconfigure(0, weight=1)
        # ===== Vars =====
        self.var_jump_key = tk.StringVar(value='alt')
        self.var_attack_key = tk.StringVar(value='shift')

        self.var_monster_dir = tk.StringVar()
        self.var_hp_pct = tk.IntVar(value=dv.HP_PERCENT)
        self.var_mp_pct = tk.IntVar(value=dv.MP_PERCENT)
        self.var_hp_key = tk.StringVar(value=dv.HP_KEY)
        self.var_mp_key = tk.StringVar(value=dv.MP_KEY)

        # 공격 사거리(px)
        self.var_rng_front = tk.IntVar(value=dv.RANGE_FRONT)
        self.var_rng_back  = tk.IntVar(value=dv.RANGE_BACK)
        self.var_rng_up    = tk.IntVar(value=dv.RANGE_UP)
        self.var_rng_down  = tk.IntVar(value=dv.RANGE_DOWN)

        # 템플레이트(이미지 경로)
        self.var_mm_tl   = tk.StringVar()  # minimap top-left
        self.var_mm_br   = tk.StringVar()  # minimap bottom-right
        self.var_mm_me   = tk.StringVar()  # minimap player
        self.var_mm_other= tk.StringVar()  # minimap other
        self.var_chr_hp  = tk.StringVar()  # character HP bar
        self.var_chr_mp  = tk.StringVar()  # character MP bar
        self.var_chr_name= tk.StringVar()  # character name
        self.var_misc_revive = tk.StringVar()  

        self._buff_rows = []  # type: list[_BuffRow]

        btns = ttk.Frame(self,padding=10)
        btns.grid(row=0, column=0, sticky="ew")
        self.btn_apply = ttk.Button(btns, text="✅ 적용", command=self._apply)
        self.btn_save  = ttk.Button(btns, text="💾 저장", command=self._save_json)
        self.btn_load  = ttk.Button(btns, text="📂 불러오기", command=self._load_json)
        self.btn_reset = ttk.Button(btns, text="초기화", command=self._reset)

        self.btn_apply.grid(row=0, column=1, padx=(0,6), pady=(0,6))
        self.btn_save.grid (row=0, column=2, padx=6,      pady=(0,6))
        self.btn_load.grid (row=0, column=3, padx=6,      pady=(0,6))
        self.btn_reset.grid(row=0, column=4, padx=(6,0),  pady=(0,6))

        self._create_required_feild(1)
        self._create_template_images_feild(2)
        self._create_attack_range_feild(3)
        self._create_potion_feild(4)
        self._create_buff_feild(5)

        self._init_locking_support()


    def _init_locking_support(self):
        """잠글 대상 위젯 수집 + 콤보박스 원래 상태 보관."""
        # 초기화 버튼은 잠그지 않음(항상 사용 가능)
        self._lock_whitelist = { self.btn_reset }
        self._lock_widgets = []
        self._combobox_default = {}  # Combobox 원래 상태(예: 'readonly')

        def walk(parent):
            for w in parent.winfo_children():
                walk(w)
                # 잠글 대상: Entry/Spinbox/Combobox/Button 등
                lockable = (
                    isinstance(w, (ttk.Entry, ttk.Spinbox, ttk.Combobox, ttk.Button))
                    or w.winfo_class() in ("TEntry", "TSpinbox", "TCombobox", "TButton")
                )
                if not lockable:
                    continue
                if w in self._lock_whitelist:
                    continue
                self._lock_widgets.append(w)
                # Combobox의 원래 상태 저장 (readonly 복원용)
                try:
                    if isinstance(w, ttk.Combobox):
                        self._combobox_default[w] = w.cget("state")  # 'normal' or 'readonly'
                except Exception:
                    pass
        walk(self)        
    def _lock_settings(self):
        """적용 이후: 모든 입력과 버튼(초기화 제외) 비활성화."""
        for w in self._lock_widgets:
            try:
                if isinstance(w, ttk.Combobox):
                    w.configure(state="disabled")
                else:
                    w.configure(state="disabled")
            except Exception:
                # 일부 기본 tk 위젯 호환
                try: w['state'] = 'disabled'
                except Exception: pass

    def _unlock_settings(self):
        """초기화 이후: 입력/버튼 원복."""
        for w in self._lock_widgets:
            try:
                if isinstance(w, ttk.Combobox):
                    # 원래 combobox 상태로 복원 (예: 'readonly')
                    state = self._combobox_default.get(w, "normal")
                    w.configure(state=state)
                else:
                    w.configure(state="normal")
            except Exception:
                try: w['state'] = 'normal'
                except Exception: pass

    def get_config(self) -> sd.SettingsConfig:
        cfg = sd.SettingsConfig(
            monster_dir=self.var_monster_dir.get().strip(),
            hp_pct=sd._clamp_int(self.var_hp_pct.get(), 0, 100, dv.HP_PERCENT),
            mp_pct=sd._clamp_int(self.var_mp_pct.get(), 0, 100, dv.MP_PERCENT),
            hp_key=(self.var_hp_key.get() or dv.HP_KEY).strip(),   # ← 추가
            mp_key=(self.var_mp_key.get() or dv.MP_KEY).strip(),   # ← 추가
            jump_key = (self.var_jump_key.get() or dv.JUMP_KEY).strip(),   # ← 추가
            attack_key = (self.var_attack_key.get() or dv.ATTACK_KEY).strip(),   # ← 추가
            attack_range=sd.AttackRange(
                front=sd._clamp_int(self.var_rng_front.get(), 0, 5000, dv.RANGE_FRONT),
                back=sd._clamp_int(self.var_rng_back.get(), 0, 5000, dv.RANGE_BACK),
                up=sd._clamp_int(self.var_rng_up.get(), 0, 5000, dv.RANGE_UP),
                down=sd._clamp_int(self.var_rng_down.get(), 0, 5000, dv.RANGE_DOWN),
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
            buffs=[r.to_model() for r in self._buff_rows],
            
        )
        return cfg
    def set_config(self, cfg):
        if isinstance(cfg, dict):
            cfg = sd.SettingsConfig.from_dict(cfg)
        if not isinstance(cfg, sd.SettingsConfig):
            return

        self.var_monster_dir.set(cfg.monster_dir)
        self.var_hp_pct.set(getattr(cfg, "hp_pct", dv.HP_PERCENT))
        self.var_mp_pct.set(getattr(cfg, "hp_pct", dv.MP_PERCENT))
        self.var_hp_key.set(getattr(cfg, "hp_key", dv.HP_KEY))  
        self.var_mp_key.set(getattr(cfg, "mp_key", dv.MP_KEY))  
        self.var_jump_key.set(getattr(cfg, "jump_key", dv.JUMP_KEY))
        self.var_attack_key.set(getattr(cfg, "attack_key", dv.ATTACK_KEY))

        self.var_rng_front.set(getattr(cfg.attack_range, 'front', dv.RANGE_FRONT))
        self.var_rng_back.set(getattr(cfg.attack_range, 'back', dv.RANGE_BACK))
        self.var_rng_up.set(getattr(cfg.attack_range, 'up', dv.RANGE_UP))
        self.var_rng_down.set(getattr(cfg.attack_range, 'down', dv.RANGE_DOWN))

        self.var_mm_tl.set(cfg.templates.minimap.top_left)
        self.var_mm_br.set(cfg.templates.minimap.bottom_right)
        self.var_mm_me.set(cfg.templates.minimap.player)
        self.var_mm_other.set(cfg.templates.minimap.other)

        self.var_chr_hp.set(cfg.templates.character.hp_bar)
        self.var_chr_mp.set(cfg.templates.character.mp_bar)
        self.var_chr_name.set(cfg.templates.character.name)

        self.var_misc_revive.set(getattr(cfg.templates.misc, "revive_message", ""))  # ← 추가

        for r in list(self._buff_rows):
            r.destroy()
        self._buff_rows.clear()
        for b in (cfg.buffs or []):
            self._add_buff_row(b)
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
        
        self.var_hp_pct.set(dv.HP_PERCENT)
        self.var_mp_pct.set(dv.MP_PERCENT)
        self.var_hp_key.set(dv.HP_KEY)
        self.var_mp_key.set(dv.MP_KEY) 
        self.var_jump_key.set(dv.JUMP_KEY) 
        self.var_attack_key.set(dv.ATTACK_KEY) 
        self.var_rng_front.set(dv.RANGE_FRONT)
        self.var_rng_back.set(dv.RANGE_BACK)
        self.var_rng_up.set(dv.RANGE_UP)
        self.var_rng_down.set(dv.RANGE_DOWN)
        self.var_misc_revive.set("")

        
        for v in (self.var_mm_tl, self.var_mm_br, self.var_mm_me, self.var_mm_other, self.var_chr_hp, self.var_chr_mp, self.var_chr_name):
            v.set("")
    def _apply(self, show_msg = True):
        cfg = self.get_config()
        
        if cfg.monster_dir == "":
            messagebox.showwarning("필수", "몬스터 폴더를 선택 후 적용해주세요.")
            return
        elif utils.validate_input(cfg.monster_dir)['is_folder'] != True:
            messagebox.showwarning("형식 불일치", "입력 값이 폴더 형식이 아닙니다.\n몬스터 폴더를 다시 선택 후 적용해주세요.")
            return
        elif cfg.templates.character.name == "":
            messagebox.showwarning("필수", "캐릭터(이름) 이미지를 선택 후 후 적용해주세요.")
            return
        elif utils.validate_input(cfg.templates.character.name)['is_image_file'] != True:
            messagebox.showwarning("형식 불일치", "입력 값이 폴더 형식이 아닙니다.\n몬스터 폴더를 다시 선택 후 적용해주세요.")
            return
        elif cfg.jump_key == "":
            messagebox.showwarning("필수", "점프 키 입력 후 적용해주세요.")
            return
        elif cfg.attack_key == "":
            messagebox.showwarning("필수", "공격 키 입력 후 적용해주세요.")
            return
        if show_msg and config.macro_thread == None and config.macro_thread.is_alive() == False:
            messagebox.showinfo("적용됨", "설정이 적용되었습니다.")
        config.setting_data = cfg
        config.gui.monitor.refresh_routine()
        config.gui.monitor.refresh_labels()
        self.start_bot()
    
    def start_bot(self):
        """최초 시작 또는 재시작 버튼 핸들러(메인 스레드에서 호출)."""
        # 이미 실행 중이면 먼저 정지
        if config.macro_thread and config.macro_thread.is_alive():
            self._stop_bot_thread()

        # 새로운 종료 이벤트 생성
        config.macro_shutdown_evt = threading.Event()

        # 새 스레드 생성 후 시작 (스레드 객체를 변수에 저장하고, 그 다음 .start())
        t = threading.Thread(
            target=self._start_modules_thread,
            daemon=True,
            name="MacroController",
        )
        config.macro_thread = t
        t.start()
    def stop_bot(self):
        """정지 버튼이 따로 있다면 이걸 호출."""
        self._stop_bot_thread()
    
    def _show_stopping_dialog(self):
        print("_show_stopping_dialog")
        if getattr(self, "_stop_dlg", None):
            return
        import tkinter as tk
        from tkinter import ttk
        dlg = tk.Toplevel(self)
        dlg.title("중지 중…")
        dlg.geometry("280x100+200+200")
        dlg.transient(self)
        dlg.grab_set()  # 선택: 모달처럼
        ttk.Label(dlg, text="모듈을 정리하는 중입니다…").pack(pady=10)
        pb = ttk.Progressbar(dlg, mode="indeterminate")
        pb.pack(fill="x", padx=16, pady=8)
        pb.start(12)
        self._stop_dlg = (dlg, pb)

    def _hide_stopping_dialog(self):
        dlg_pair = getattr(self, "_stop_dlg", None)
        if not dlg_pair:
            return
        dlg, pb = dlg_pair
        try:
            pb.stop()
            dlg.grab_release()
            dlg.destroy()
        except Exception:
            pass
        self._stop_dlg = None

    
    def _stop_bot_thread(self):
        """실행 중인 컨트롤러/모듈을 정리하고 스레드를 종료."""

        evt = config.macro_shutdown_evt
        if evt:
            evt.set()  # 종료 신호 전파

        # 각 모듈에 stop()이 있다면 호출 (없으면 무시)
        for m in (config.listener, config.bot, config.capture, config.notifier):
            try:
                if m and hasattr(m, 'stop'):
                    m.stop()
            except Exception as e:
                print(f"[WARN] stop() 실패: {m}: {e}")

        # 컨트롤러 스레드 합류 대기 (최대 5초)
        t = config.macro_thread
        if t and t.is_alive():
            t.join(timeout=5)

        # 레퍼런스 정리
        config.macro_thread = None
        config.macro_shutdown_evt = None
        config.bot = config.capture = config.listener = config.notifier = None

        # UI는 메인 스레드에서
        
        self.after(0, lambda: messagebox.showinfo("중지", "모듈을 중지했습니다."))

    
    def _start_modules_thread(self):
        """모듈을 순서대로 시작하고, 종료 이벤트가 올 때까지 생명주기를 관리."""
        try:
            shutdown_evt = config.macro_shutdown_evt
            self.after(0, self._show_stopping_dialog)

            # 인스턴스 생성 + 전역 등록
            config.bot = Bot()      # ← 없다면 생성 후 속성으로 주입
            config.capture = Capture()
            config.notifier = Notifier()
            config.listener = Listener()

            # 시작 + 준비 대기
            config.capture.start()
            if not self._wait(lambda: config.capture.ready, 10, shutdown_evt):
                return self._fail("Capture가 준비되지 않습니다.")

            config.bot.start()
            if not self._wait(lambda: config.bot.ready, 5, shutdown_evt):
                return self._fail("Bot이 준비되지 않습니다.")

            config.listener.start()
            if not self._wait(lambda: config.listener.ready, 5, shutdown_evt):
                return self._fail("Listener가 준비되지 않습니다.")

            config.notifier.start()
            if not self._wait(lambda: config.notifier.ready, 5, shutdown_evt):
                return self._fail("Notifier가 준비되지 않습니다.")

            # 메인스레드로 UI 알림
            self.after(0, lambda: messagebox.showinfo("시작", "모듈이 모두 준비되었습니다.\n f9를 눌러서 시작/일시 정지 할 수 있습니다."))
            self.after(0, self._hide_stopping_dialog)
            # 종료 신호가 올 때까지 대기 (컨트롤러 스레드의 생명 유지)
            while not shutdown_evt.is_set():
                time.sleep(0.2)

        except Exception as e:
            print(f"[ERROR] _start_modules_thread: {e}")
            self.after(0, lambda: messagebox.showerror("시작 실패", str(e)))
        finally:
            # 안전한 정리
            for m in (config.listener, config.notifier, config.bot, config.capture):
                try:
                    if m and hasattr(m, 'stop'):
                        m.stop()
                except Exception as e:
                    print(f"[WARN] stop during finally: {m}: {e}")
                

    def _wait(self, pred, timeout_sec: float, shutdown_evt=None):
        """pred()가 True가 되거나 timeout, 혹은 종료 이벤트가 set될 때까지 대기."""
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            if shutdown_evt is not None and shutdown_evt.is_set():
                return False
            try:
                if pred():
                    return True
            except Exception:
                pass
            time.sleep(0.05)
        return False

    def _fail(self, msg: str):
        # 메인 스레드로 띄우기
        self.after(0, lambda: messagebox.showerror("오류", msg))
        return False


class _BuffRow:
    def __init__(self, master, on_remove):
        self.master = master
        self.on_remove = on_remove
        self.var_cd = tk.IntVar(value=0)
        self.var_key = tk.StringVar(value="")

        self.spn_cd = ttk.Spinbox(master, from_=0, to=36000, width=8,
                                  textvariable=self.var_cd, justify="right")
        self.ent_key = ttk.Entry(master, textvariable=self.var_key)
        self.btn_del = ttk.Button(master, text="삭제", command=lambda: on_remove(self))
        

    def grid(self, row: int):
        self.spn_cd.grid(row=row, column=0, sticky="w", pady=2)
        self.ent_key.grid(row=row, column=1, sticky="ew", padx=(6,6), pady=2)
        self.btn_del.grid(row=row, column=2, sticky="e", pady=2)

    def destroy(self):
        for w in (self.spn_cd, self.ent_key, self.btn_del):
            w.destroy()

    # 모델 변환
    def to_model(self) -> sd.BuffSettings:
        return sd.BuffSettings(
            cooldown_sec=sd._clamp_int(self.var_cd.get(), 0, 36000, 0),
            key=self.var_key.get().strip()
        )

    def from_model(self, m: sd.BuffSettings):
        self.var_cd.set(sd._clamp_int(getattr(m, "cooldown_sec", 0), 0, 36000, 0))
        self.var_key.set(str(getattr(m, "key", "")).strip())
