
from src.gui.interfaces import Tab
import tkinter as tk
from tkinter import ttk
from src.gui.monitor.minimap import Minimap
from src.common import config
ROUTINE_COLS = ("idx","action","x","y")
class Monitor(Tab):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, "모니터", **kwargs)

        self.grid_columnconfigure(0, weight=1)   # 왼쪽 리스트
        self.grid_columnconfigure(1, weight=0)   # 오른쪽(미니맵/라벨)
        self.grid_rowconfigure(0, weight=1)

        # ▶ 왼쪽: 루틴 리스트
        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)

        self.routine_tree = ttk.Treeview(left, columns=ROUTINE_COLS, show="headings", height=18)
        for c, w in zip(ROUTINE_COLS, (50,90,70,70,80,90,80)):
            self.routine_tree.heading(c, text=c)
            self.routine_tree.column(c, width=w, anchor="center")
        self.routine_tree.grid(row=0, column=0, sticky="nsew")

        yscroll = ttk.Scrollbar(left, orient="vertical", command=self.routine_tree.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        self.routine_tree.configure(yscrollcommand=yscroll.set)

        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="n", padx=10, pady=10)
        right.columnconfigure(0, weight=1)
        
        self.minimap = Minimap(right)
        self.minimap.grid(row=0, column=0, sticky="nsew")

        # ---- Status 그룹 (미니맵 아래) ----
        status = ttk.LabelFrame(right, text="Status",labelanchor='n')
        status.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        status.columnconfigure(1, weight=1)

        ttk.Label(status, text="Bot 상태:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.bot_status_var = tk.StringVar()
        self.bot_status_label = ttk.Label(status, textvariable=self.bot_status_var)
        self.bot_status_label.grid(row=0, column=1, sticky="w", padx=5, pady=2)

        # 게임 설정 상태
        ttk.Label(status, text="게임 설정:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.game_setting_var = tk.StringVar()
        self.game_setting_label = ttk.Label(status, textvariable=self.game_setting_var)
        self.game_setting_label.grid(row=1, column=1, sticky="w", padx=5, pady=2)

        # 루틴 상태
        ttk.Label(status, text="루틴:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.routine_var = tk.StringVar()
        self.routine_label = ttk.Label(status, textvariable=self.routine_var)
        self.routine_label.grid(row=2, column=1, sticky="w", padx=5, pady=2)
        
        self.refresh_labels()
        self.refresh_routine()


    def set_enable(self):
        if config.setting_data == None:
            self.bot_status_var.set("게임 설정 준비 전")
        elif config.routine == None:
            self.bot_status_var.set("루틴 설정 준비 전")
        elif config.enabled:
            self.bot_status_var.set("작동 중")
        else:
            self.bot_status_var.set("준비 완료 / 멈춤")

    def refresh_labels(self):
        self.set_enable()
        self.set_label(config.setting_data is not None, is_setting=True)
        self.set_label(bool(config.routine), is_setting=False)

    def set_label(self, value, is_setting) :
        if is_setting:
            text = '적용 되었습니다' if value else "게임 설정 탭에서 설정을 적용해주세요"    
            self.game_setting_var.set(text)
        else:

            text = '적용 되었습니다' if value else "루틴 설정 탭에서 루틴을 적용해주세요"    
            self.routine_var.set(text)


    # ====== 루틴 트리 갱신 (config.routine 또는 전달된 data 사용) ======
    def refresh_routine(self, current_index=0):
        if config.routine == None:
            return
        print('refresh_routine')
        items = config.routine.items
        self.routine_tree.delete(*self.routine_tree.get_children())

        # 하이라이트 색상 태그 정의
        self.routine_tree.tag_configure("highlight", background="#ffe08c")  # 연한 노랑

        for i, d in enumerate(items, start=0):
            # dataclass(ActionItem)과 dict 모두 지원
            get = (lambda k: getattr(d, k)) if hasattr(d, "__dict__") else (lambda k: d.get(k, ""))

            # 현재 인덱스면 highlight 태그 적용
            tags = ("highlight",) if current_index is not None and i == current_index else ()

            self.routine_tree.insert(
                "", "end",
                values=(
                    i,
                    get("action"), get("x"), get("y"),
                ),
                tags=tags
            )
                

