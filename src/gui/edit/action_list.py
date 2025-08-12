import json
from tkinter import ttk, filedialog, messagebox
from src.modules.bot import RoutePatrol
from src.datas.routine_data import ActionItem, list_to_jsonable, list_from_jsonable
from src.common  import config


class ActionList(ttk.Frame):
    """왼쪽 리스트(트리뷰) + 툴바."""
    def __init__(self, master, on_select, **kwargs):
        super().__init__(master, padding=12, **kwargs)
        self.on_select = on_select

        # 레이아웃 뼈대: [row0=topbar][row1=list][row2=bottombar]
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)  # 리스트가 가운데서 확장

         # Topbar
        topbar = ttk.Frame(self)
        topbar.grid(row=0, column=0, sticky="ew")
        self.btn_save  = ttk.Button(topbar, text="💾 저장",     command=self._save_json)
        self.btn_load  = ttk.Button(topbar, text="📂 불러오기", command=self._load_json)
        self.btn_apply = ttk.Button(topbar, text="✅ 적용",     command=self._apply)
        self.btn_save.grid(row=0, column=0, padx=(0,6), pady=(0,6))
        self.btn_load.grid(row=0, column=1, padx=6,      pady=(0,6))
        self.btn_apply.grid(row=0, column=2, padx=(6,0),  pady=(0,6))

        # List 영역 (grid) — 래퍼 프레임 사용
        listwrap = ttk.Frame(self)
        listwrap.grid(row=1, column=0, sticky="nsew")
        listwrap.columnconfigure(0, weight=1)
        listwrap.rowconfigure(0, weight=1)

        cols = ("idx","action","x","y","end_y","duration","count")
        self.tree = ttk.Treeview(listwrap, columns=cols, show="headings")
        for c, w in zip(cols, (50,90,70,70,80,90,80)):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")

        yscroll = ttk.Scrollbar(listwrap, orient="vertical", command=self.tree.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=yscroll.set)

        # ── 하단: 삭제 / 위로 / 아래로 ──────────────────────────
        bottombar = ttk.Frame(self)
        bottombar.grid(row=2, column=0, sticky="ew", pady=(6,0))
        bottombar.columnconfigure((0,1,2), weight=1)

        self.btn_del = ttk.Button(bottombar, text="🗑 삭제", command=self._delete_selected)
        self.btn_up  = ttk.Button(bottombar, text="▲ 위로", command=lambda: self._move_selected(-1))
        self.btn_dn  = ttk.Button(bottombar, text="▼ 아래로", command=lambda: self._move_selected(1))

        self.btn_del.grid(row=0, column=0, sticky="ew", padx=(0,4))
        self.btn_up.grid(row=0, column=1, sticky="ew", padx=4)
        self.btn_dn.grid(row=0, column=2, sticky="ew", padx=(4,0))

        self.data: list[ActionItem] = []
        self.edit_index: int | None = None

    def _apply(self, show_msg = True):
        if len(self.data) < 1:
            messagebox.showwarning("확인", "엑션은 한 개 이상 지정해주세요.")
            return
        config.routine = RoutePatrol(self.data)   
        config.gui.monitor.refresh_routine()
        config.gui.monitor.refresh_labels()
        if show_msg:
            messagebox.showinfo("적용됨", "루틴 설정이 적용되었습니다.")
        
    # ActionList 클래스 내부에 메서드 추가
    def _load_json(self):
        path = filedialog.askopenfilename(
            title="JSON 불러오기",
            filetypes=[("JSON files","*.json"),("All files","*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                arr = json.load(f)
            if not isinstance(arr, list):
                raise ValueError("최상위가 리스트여야 합니다.")
            items = list_from_jsonable(arr)  # ← 검증 포함

            # 간단 검증: 필수 키 확인 (x, y, action)
            self.data = items
            self._refresh_tree()
            messagebox.showinfo("불러오기/적용 완료", f"항목 {len(self.data)}개 불러왔습니다.")
            self.event_generate("<<ActionListUpdated>>")
            
            self._apply(show_msg=False)
        except Exception as e:
            messagebox.showerror("불러오기 실패", str(e))

    def _on_select(self, *_):
        sel = self._get_selected_index()
        if sel is not None:
            self.edit_index = sel

    def _on_double_click(self, *_):
        sel = self._get_selected_index()
        if sel is not None:
            self.edit_index = sel
            self.on_select(self.data[sel])

    def _get_selected_index(self):
        sel = self.tree.selection()
        if not sel:
            return None
        item_id = sel[0]
        # 첫 번째 컬럼(idx)에 실제 인덱스 표시
        idx_text = self.tree.item(item_id, "values")[0]
        try:
            return int(idx_text) - 1
        except ValueError:
            return None

    def add_item(self, it: ActionItem):
        self.data.append(it); self._refresh_tree()

    def update_item(self, it: ActionItem):
        if self.edit_index is None: return
        self.data[self.edit_index] = it
        self._refresh_tree(); self.edit_index = None

    def clear_edit_state(self):
        self.edit_index = None
        self.tree.selection_remove(self.tree.selection())

    def _refresh_tree(self):
        for i, it in enumerate(self.data, start=1):
            self.tree.insert("", "end", values=(
                i, it.action, it.x, it.y,
                "" if it.end_y is None else it.end_y,
                "" if it.duration is None else it.duration,
                "" if it.count is None else it.count,
            ))

    def _delete_selected(self):
        sel = self._get_selected_index()
        if sel is None:
            return
        del self.data[sel]
        self._refresh_tree()
        self.edit_index = None

    def _move_selected(self, delta):
        sel = self._get_selected_index()
        if sel is None:
            return
        new_idx = sel + delta
        if not (0 <= new_idx < len(self.data)):
            return
        self.data[sel], self.data[new_idx] = self.data[new_idx], self.data[sel]
        self._refresh_tree()
        # 새 위치 다시 선택
        for item in self.tree.get_children():
            vals = self.tree.item(item, "values")
            if int(vals[0]) == new_idx + 1:
                self.tree.selection_set(item)
                self.tree.see(item)
                break

    def _save_json(self):
        path = filedialog.asksaveasfilename(
            title="JSON으로 저장",
            defaultextension=".json",
            filetypes=[("JSON files","*.json"),("All files","*.*")]
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(list_to_jsonable(self.data), f, ensure_ascii=False, indent=2)
        messagebox.showinfo("저장 완료", f"저장됨:\n{path}")

    def _copy_json(self):
        payload = json.dumps(self.data, ensure_ascii=False, indent=2)
        self.clipboard_clear()
        self.clipboard_append(payload)
        messagebox.showinfo("클립보드", "JSON이 클립보드에 복사되었습니다.")

    def set_data(self, items):
        """외부에서 루틴 전체를 주입"""
        self.data = list(items or [])
        self._refresh_tree()
        # 다른 곳(모니터/미니맵 등)에 알리려면 이벤트 쏘기
        self.event_generate("<<ActionListUpdated>>", when="tail")

