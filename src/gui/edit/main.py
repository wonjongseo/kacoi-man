import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from src.gui.view.minimap import Minimap
from src.gui.interfaces import Tab

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

        self.minimap = Minimap(self)
        self.minimap.grid(row=11, column=0, columnspan=2, sticky="nsew", pady=(10,0))
        self.minimap.rowconfigure(0, weight=1)
        self.minimap.columnconfigure(0, weight=1)


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

    def get_payload(self):
        """현재 폼 값으로 dict 생성 (액션별 필드 포함)."""
        x = self._parse_int(self.var_x.get(), "x")
        y = self._parse_int(self.var_y.get(), "y")
        action = self.var_action.get()
        payload = {"x": x, "y": y, "action": action}

        if action == "ladder":
            payload["end_y"] = self._parse_int(self.var_end_y.get(), "end_y")
        elif action == "wait":
            payload["duration"] = self._parse_int(self.var_duration.get(), "duration")
        elif action == "jump":
            payload["count"] = self._parse_int(self.var_count.get(), "count")

        return payload

    def set_payload(self, d: dict):
        """트리에서 선택한 항목을 폼에 채우기."""
        self.var_x.set(str(d.get("x","")))
        self.var_y.set(str(d.get("y","")))
        self.var_action.set(d.get("action","move"))
        self._on_action_change()
        self.var_end_y.set(str(d.get("end_y","")))
        self.var_duration.set(str(d.get("duration","")))
        self.var_count.set(str(d.get("count","")))
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


class ActionList(ttk.Frame):
    """왼쪽 리스트(트리뷰) + 툴바."""
    def __init__(self, master, on_select, **kwargs):
        super().__init__(master, padding=12, **kwargs)
        self.on_select = on_select

        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(side="top", fill="x")
        self.btn_del = ttk.Button(toolbar, text="🗑 삭제", command=self._delete_selected)
        self.btn_del.pack(side="left")
        self.btn_up = ttk.Button(toolbar, text="▲ 위로", command=lambda: self._move_selected(-1))
        self.btn_up.pack(side="left", padx=4)
        self.btn_dn = ttk.Button(toolbar, text="▼ 아래로", command=lambda: self._move_selected(1))
        self.btn_dn.pack(side="left", padx=(0,8))

        self.btn_copy = ttk.Button(toolbar, text="📋 클립보드 복사", command=self._copy_json)
        self.btn_copy.pack(side="right")
        self.btn_save = ttk.Button(toolbar, text="💾 JSON 저장", command=self._save_json)
        self.btn_save.pack(side="right", padx=(0,6))

        # Tree
        cols = ("idx","action","x","y","end_y","duration","count")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=16)
        for c, w in zip(cols, (50,90,70,70,80,90,80)):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True, pady=(8,0))

        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", self._on_double_click)

        self.data = []        # 실제 데이터(list of dict)
        self.edit_index = None

   
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
                data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("최상위가 리스트여야 합니다.")
            # 간단 검증: 필수 키 확인 (x, y, action)
            for i, d in enumerate(data, start=1):
                if not isinstance(d, dict):
                    raise ValueError(f"{i}번째 항목이 객체가 아닙니다.")
                for k in ("x","y","action"):
                    if k not in d:
                        raise ValueError(f"{i}번째 항목에 '{k}'가 없습니다.")
            self.data = data
            self._refresh_tree()
            messagebox.showinfo("불러오기 완료", f"항목 {len(self.data)}개 불러왔습니다.")
            # 미리보기 갱신 요청 (App 쪽에 콜백 줄 수도 있지만 간단히 이벤트로 처리)
            self.event_generate("<<ActionListUpdated>>")
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

    def add_item(self, d: dict):
        self.data.append(d)
        self._refresh_tree()

    def update_item(self, d: dict):
        if self.edit_index is None:
            return
        self.data[self.edit_index] = d
        self._refresh_tree()
        self.edit_index = None

    def clear_edit_state(self):
        self.edit_index = None
        self.tree.selection_remove(self.tree.selection())

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for i, d in enumerate(self.data, start=1):
            self.tree.insert("", "end", values=(
                i, d.get("action",""),
                d.get("x",""), d.get("y",""),
                d.get("end_y",""), d.get("duration",""), d.get("count","")
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
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("저장 완료", f"저장됨:\n{path}")

    def _copy_json(self):
        payload = json.dumps(self.data, ensure_ascii=False, indent=2)
        self.clipboard_clear()
        self.clipboard_append(payload)
        messagebox.showinfo("클립보드", "JSON이 클립보드에 복사되었습니다.")


class Edit(Tab):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, 'Edit', **kwargs)
       
        self._apply_style()

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(0, weight=1)

        self.list_panel = ActionList(container, on_select=self._load_to_form)
        self.list_panel.grid(row=0, column=0, sticky="nsew")

        self.form_panel = ActionForm(
            container,
            on_submit=self._add_item,
            on_clear=self._clear_selection,
            on_update=self._update_item
        )
        self.form_panel.grid(row=0, column=1, sticky="nsew")

       


    def _apply_style(self):
        style = ttk.Style()
        # 가능한 경우 'clam' 테마 사용
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

    # 연결 함수들
    def _add_item(self, d):
        self.list_panel.add_item(d)

    def _update_item(self, d):
        self.list_panel.update_item(d)

    def _clear_selection(self):
        self.list_panel.clear_edit_state()

    def _load_to_form(self, d):
        self.form_panel.set_payload(d)

if __name__ == "__main__":
    App().mainloop()
