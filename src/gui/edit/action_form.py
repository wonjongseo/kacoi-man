import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from src.gui.monitor.minimap import Minimap
from src.gui.interfaces import Tab
from src.datas.routine_data import ActionItem


ACTIONS = ("move", "jump", "wait", "ladder")

class ActionForm(ttk.Frame):
    """오른쪽 입력 폼: 공통(x,y,action) + 액션별 필드(조건부)."""
    def __init__(self, master, on_submit, on_clear, on_update, **kwargs):
        super().__init__(master, padding=12, **kwargs)
        self.on_submit = on_submit
        self.on_clear = on_clear
        self.on_update = on_update

        # Vars
        self.var_x = tk.StringVar()
        self.var_y = tk.StringVar()
        self.var_action = tk.StringVar(value=ACTIONS[0])
        self.var_end_y = tk.StringVar()     # ladder 전용
        self.var_duration = tk.StringVar()  # wait 전용
        self.var_count = tk.StringVar()     # jump 전용

        # Grid
        self.rowconfigure(11, weight=1)              # 미니맵 영역이 세로로 늘어나도록
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)


        # 공통 필드
        ttk.Label(self, text="action").grid(row=0, column=0, sticky="w", pady=(0,6))
        self.cb_action = ttk.Combobox(self, values=ACTIONS, textvariable=self.var_action, state="readonly")
        self.cb_action.grid(row=0, column=1, sticky="ew", pady=(0,6))
        self.cb_action.bind("<<ComboboxSelected>>", self._on_action_change)

        ttk.Label(self, text="x").grid(row=1, column=0, sticky="w")
        self.ent_x = ttk.Entry(self, textvariable=self.var_x)
        self.ent_x.grid(row=1, column=1, sticky="ew", pady=2)

        ttk.Label(self, text="y").grid(row=2, column=0, sticky="w")
        self.ent_y = ttk.Entry(self, textvariable=self.var_y)
        self.ent_y.grid(row=2, column=1, sticky="ew", pady=2)

        # 조건부 컨테이너
        self.conditional = ttk.Frame(self)
        self.conditional.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8,4))
        self.conditional.columnconfigure(1, weight=1)

        # ladder: end_y
        self.row_ladder = ttk.Frame(self.conditional)
        ttk.Label(self.row_ladder, text="end_y").grid(row=0, column=0, sticky="w")
        self.ent_end_y = ttk.Entry(self.row_ladder, textvariable=self.var_end_y)
        self.ent_end_y.grid(row=0, column=1, sticky="ew", pady=2)
        self.row_ladder.columnconfigure(1, weight=1)

        # wait: duration
        self.row_wait = ttk.Frame(self.conditional)
        ttk.Label(self.row_wait, text="duration").grid(row=0, column=0, sticky="w")
        self.ent_duration = ttk.Entry(self.row_wait, textvariable=self.var_duration)
        self.ent_duration.grid(row=0, column=1, sticky="ew", pady=2)
        self.row_wait.columnconfigure(1, weight=1)

        # jump: count
        self.row_jump = ttk.Frame(self.conditional)
        ttk.Label(self.row_jump, text="count").grid(row=0, column=0, sticky="w")
        self.ent_count = ttk.Entry(self.row_jump, textvariable=self.var_count)
        self.ent_count.grid(row=0, column=1, sticky="ew", pady=2)
        self.row_jump.columnconfigure(1, weight=1)

        # 버튼들
        btns = ttk.Frame(self)
        btns.grid(row=10, column=0, columnspan=2, sticky="ew", pady=(10,0))
        btns.columnconfigure((0,1,2), weight=1)
        self.btn_add = ttk.Button(btns, text="＋ 추가", command=self._submit)
        self.btn_add.grid(row=0, column=0, sticky="ew", padx=(0,4))
        self.btn_update = ttk.Button(btns, text="✔ 업데이트", command=self._update, state="disabled")
        self.btn_update.grid(row=0, column=1, sticky="ew", padx=4)
        self.btn_clear = ttk.Button(btns, text="새로 입력", command=self._clear)
        self.btn_clear.grid(row=0, column=2, sticky="ew", padx=(4,0))

        self.minimap = Minimap(self)
        self.minimap.grid(row=11, column=0, columnspan=2, sticky="nsew", pady=(10,0))
        self.minimap.rowconfigure(0, weight=1)
        self.minimap.columnconfigure(0, weight=1)


        self._on_action_change()  # 초기 표시

    def _on_action_change(self, *_):
        # 모든 조건부 숨김
        for w in (self.row_ladder, self.row_wait, self.row_jump):
            w.grid_forget()
        # 현재 액션에 맞는 필드만 보이기
        act = self.var_action.get()
        if act == "ladder":
            self.row_ladder.grid(row=0, column=0, sticky="ew")
        elif act == "wait":
            self.row_wait.grid(row=0, column=0, sticky="ew")
        elif act == "jump":
            self.row_jump.grid(row=0, column=0, sticky="ew")

    def _parse_int(self, s, field_name):
        try:
            return int(s)
        except ValueError:
            raise ValueError(f"'{field_name}'는 정수여야 합니다.")


    def get_payload(self) -> ActionItem:
        x = self._parse_int(self.var_x.get(), "x")
        y = self._parse_int(self.var_y.get(), "y")
        action = self.var_action.get()

        item = ActionItem(
            action=action, x=x, y=y,
            end_y=int(self.var_end_y.get()) if action=="ladder" and self.var_end_y.get()!="" else None,
            duration=int(self.var_duration.get()) if action=="wait" and self.var_duration.get()!="" else None,
            count=int(self.var_count.get()) if action=="jump" and self.var_count.get()!="" else None,
        )
        item.validate()
        return item


    def set_payload(self, it: ActionItem):
        self.var_x.set(str(it.x))
        self.var_y.set(str(it.y))
        self.var_action.set(it.action)
        self._on_action_change()
        self.var_end_y.set("" if it.end_y is None else str(it.end_y))
        self.var_duration.set("" if it.duration is None else str(it.duration))
        self.var_count.set("" if it.count is None else str(it.count))
        self.btn_update.config(state="normal")
        self.btn_add.config(state="disabled")

    def _submit(self):
        try:
            self.on_submit(self.get_payload())
            self._clear_fields_only()
        except Exception as e:
            messagebox.showerror("입력 오류", str(e))

    def _update(self):
        try:
            self.on_update(self.get_payload())
            self._clear()
        except Exception as e:
            messagebox.showerror("입력 오류", str(e))

    def _clear_fields_only(self):
        self.var_x.set(""); self.var_y.set("")
        self.var_end_y.set(""); self.var_duration.set(""); self.var_count.set("")

    def _clear(self):
        self._clear_fields_only()
        self.var_action.set(ACTIONS[0])
        self._on_action_change()
        self.btn_update.config(state="disabled")
        self.btn_add.config(state="normal")
        self.on_clear()



