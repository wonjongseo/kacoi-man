

import json
import os
from src.common.interfaces import Configurable
from os.path import basename, splitext
from src.common import config, utils
from src.routine import components
from types import SimpleNamespace
from src.routine.strategies import STEP_STRATEGIES

def _make_class_with_defaults(base_cls, default_kwargs: dict):
    """
    base_cls의 __init__ 기본 인자를 JSON에서 주는 default_kwargs로 "덧씌운"
    서브클래스를 동적으로 생성한다.
    """
    class _WithDefaults(base_cls):
        def __init__(self, *args, **kwargs):
            merged = dict(default_kwargs) if default_kwargs else {}
            # 위치 인자와 충돌나지 않게: kwargs 우선 → 사용자가 넘긴 값이 있으면 그것을 쓰고
            merged.update(kwargs)
            super().__init__(*args, **merged)
    _WithDefaults.__name__ = f"{base_cls.__name__}WithDefaults"
    return _WithDefaults



CB_KEYBINDING_DIR = os.path.join('resources', 'keybindings')

class CommandBook(Configurable):
    def __init__(self, file):
        self.name = splitext(basename(file))[0]
        # self.buff = TODO
        self.DEFAULT_CONFIG = {}
        result = self.load_commands(file)
        if result is None:
            raise ValueError(f"Invalid command book at '{file}'")
        
        self.dict, self.module = result
        super().__init__(self.name, directory = CB_KEYBINDING_DIR)
    
    def load_commands(self, file):
        """Prompts the user to select a command module to import. Updates config's command book."""
        utils.print_separator()
        print(f"[~] Loading command book '{basename(file)}':")

        ext = splitext(file)[1]

        if ext not in ('.py', '.json'):
            print(f" !  '{ext}' is not a supported file extension.")
            return
        
        new_step = components.step
        new_cb = {}

        for c in (components.Wait, components.Walk, components.Fall):
            new_cb[c.__name__.lower()] = c
        
        if ext == '.json':
            module = SimpleNamespace()  # .Key를 동적으로 심기 위한 placeholder
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:
                print(f" !  Failed to read JSON: {e}")
                return

            # Key 섹션
            keymap = data.get('Key', {})
            if not isinstance(keymap, dict) or not keymap:
                print(" !  Error: JSON must contain non-empty 'Key' object.")
                return
            self.DEFAULT_CONFIG = keymap

            # 동적 Key 클래스 흉내 (속성 주입 대상)
            module.Key = type('Key', (), keymap)

            # step 전략
            strat_name = data.get('step_strategy')
            if strat_name:
                if strat_name not in STEP_STRATEGIES:
                    print(f" !  Unknown step_strategy '{strat_name}'. Available: {list(STEP_STRATEGIES)}")
                    return
                components.step = STEP_STRATEGIES[strat_name]
            else:
                # 전략이 없으면 기본 step(“미구현→중단”)이므로 이동 커맨드만으로는 실행 의미가 없음.
                # 사용성이 나쁘니 안전하게 경고.
                print(" !  Warning: 'step_strategy' not provided; default 'step' will abort movement.")

            # 커맨드 디폴트 파라미터
            defaults = data.get('commands', {}) or {}

            # 기본 커맨드 등록(Wait/Walk/Fall는 이미 new_cb에 채워놨음)
            # Move/Adjust 등 나머지도 기본 등록
            base_map = {
                'move': components.Move,
                'adjust': components.Adjust,
                # 'buff': components.Buff,
                'wait': components.Wait,
                'walk': components.Walk,
                'fall': components.Fall,
            }

            # defaults에 맞춰 래퍼 클래스를 생성하여 등록
            for key, base_cls in base_map.items():
                if key in defaults and isinstance(defaults[key], dict):
                    new_cb[key] = _make_class_with_defaults(base_cls, defaults[key])
                else:
                    new_cb[key] = base_cls

            # 필수/이동 체크 로직은 PY와 동일 컨셉
            required_found = True
            # if 'buff' not in new_cb:
            #     required_found = False
            #     new_cb['buff'] = components.Buff
            #     print(" !  Error: Must implement required command 'buff' (JSON).")

            movement_found = ('move' in new_cb) and ('adjust' in new_cb)
            step_found = (components.step is not components.step.__func__) if hasattr(components.step, '__func__') else True
            # 위 라인은 파이썬 바인딩 상황에 따라 애매할 수 있으니, 간단히 전략이 있으면 OK로 간주
            step_found = strat_name is not None

            if not step_found and not movement_found:
                print(" !  Error: Must either provide 'step_strategy' or both 'move' and 'adjust' command defaults.")
                return

            print(f': {new_cb}')
            
            # 성공 처리
            # self.buff = new_cb['buff']()
            # config.gui.menu.file.enable_routine_state()
            # config.gui.view.status.set_cb(basename(file))
            # config.routine.clear()
            # print(f" ~  Successfully loaded command book (JSON) '{self.name}'")
            return new_cb, module
        

    def __getitem__(self, item):
        return self.dict[item]

    def __contains__(self, item):
        return item in self.dict

    def load_config(self):
        super().load_config()
        self._set_keybinds()

    def save_config(self):
        self._set_keybinds()
        super().save_config()

    def _set_keybinds(self):
        for k, v in self.config.items():
            setattr(self.module.Key, k, v)   