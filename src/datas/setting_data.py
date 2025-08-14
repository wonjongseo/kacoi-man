from dataclasses import dataclass, asdict, field
from typing import Dict, Any, Optional


def _clamp_int(v: Any, lo: int, hi: int, default: int = 0) -> int:
    try:
        v = int(v)
    except (TypeError, ValueError):
        v = default
    return max(lo, min(hi, v))


def _png_or_empty(p: Optional[str]) -> str:
    p = (p or "").strip()
    # 여기서 확장자 경고/검증을 하려면 .lower().endswith(".png") 체크 가능
    return p



@dataclass
class MiscTemplates:
    revive_message: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MiscTemplates":
        d = d or {}
        return cls(revive_message=_png_or_empty(d.get("revive_message")))
    
@dataclass
class AttackRange:
    front: int = 220
    back:  int = 0
    up:    int = 50
    down:  int = 50

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AttackRange":
        d = d or {}
        return cls(
            front=_clamp_int(d.get("front"), 0, 5000, 220),
            back=_clamp_int(d.get("back"),   0, 5000, 0),
            up=_clamp_int(d.get("up"),       0, 5000, 50),
            down=_clamp_int(d.get("down"),   0, 5000, 50),
        )
    def __iter__(self):
        yield self.front
        yield self.back
        yield self.up
        yield self.down

@dataclass
class BuffSettings:
    cooldown_sec: int = 0   # 버프 쿨타임(초)
    key: str = ""           # 버프 사용 키 (예: 'F1', 'Q', 'shift+a')

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BuffSettings":
        d = d or {}
        return cls(
            cooldown_sec=_clamp_int(d.get("cooldown_sec", 0), 0, 36000, 0),
            key=str(d.get("key", "")).strip()
        )

@dataclass
class MinimapTemplates:
    top_left:     str = ""
    bottom_right: str = ""
    player:       str = ""
    other:        str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MinimapTemplates":
        d = d or {}
        return cls(
            top_left=_png_or_empty(d.get("top_left")),
            bottom_right=_png_or_empty(d.get("bottom_right")),
            player=_png_or_empty(d.get("player")),
            other=_png_or_empty(d.get("other")),
        )


@dataclass
class CharacterTemplates:
    hp_bar: str = ""
    mp_bar: str = ""
    name:   str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CharacterTemplates":
        d = d or {}
        return cls(
            hp_bar=_png_or_empty(d.get("hp_bar")),
            mp_bar=_png_or_empty(d.get("mp_bar")),
            name=_png_or_empty(d.get("name")),
        )


@dataclass
class Templates:
    minimap:   MinimapTemplates = field(default_factory=MinimapTemplates)
    character: CharacterTemplates = field(default_factory=CharacterTemplates)
    misc: MiscTemplates = field(default_factory=MiscTemplates)  

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Templates":
        d = d or {}
        return cls(
            minimap=MinimapTemplates.from_dict(d.get("minimap") or {}),
            character=CharacterTemplates.from_dict(d.get("character") or {}),
            misc=MiscTemplates.from_dict(d.get("misc") or {}), 
        )


@dataclass
class SettingsConfig:
    monster_dir: str = ""
    hp_pct: int = 50
    mp_pct: int = 50
    hp_key: str = ""        # ← 추가
    mp_key: str = ""        # ← 추가
    attack_range: AttackRange = field(default_factory=AttackRange)
    templates: Templates = field(default_factory=Templates)
    buffs: BuffSettings = field(default_factory=BuffSettings)
    # ---- 직렬화 / 역직렬화 ----
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SettingsConfig":
        d = d or {}
        return cls(
            monster_dir=(d.get("monster_dir") or "").strip(),
            hp_pct=_clamp_int(d.get("hp_pct"), 0, 100, 50),
            mp_pct=_clamp_int(d.get("mp_pct"), 0, 100, 50),
            hp_key=(d.get("hp_key") or "").strip(),   # ← 추가
            mp_key=(d.get("mp_key") or "").strip(),   # ← 추가
            attack_range=AttackRange.from_dict(d.get("attack_range") or {}),
            templates=Templates.from_dict(d.get("templates") or {}),
            buffs=BuffSettings.from_dict(d.get("buffs") or {}),  
        )