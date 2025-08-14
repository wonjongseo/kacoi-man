import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from src.gui.monitor.minimap import Minimap
from src.gui.interfaces import Tab
from src.datas.routine_data import ActionItem
from src.gui.edit.action_list import ActionList
from src.gui.edit.action_form import ActionForm


class Edit(Tab):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, '루틴 설정', **kwargs)
       
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
