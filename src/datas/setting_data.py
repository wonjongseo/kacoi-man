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
class AttackRange:
    front: int = 200
    back:  int = 120
    up:    int = 120
    down:  int = 80

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AttackRange":
        d = d or {}
        return cls(
            front=_clamp_int(d.get("front"), 0, 5000, 200),
            back=_clamp_int(d.get("back"),   0, 5000, 120),
            up=_clamp_int(d.get("up"),       0, 5000, 120),
            down=_clamp_int(d.get("down"),   0, 5000, 80),
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

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Templates":
        d = d or {}
        return cls(
            minimap=MinimapTemplates.from_dict(d.get("minimap") or {}),
            character=CharacterTemplates.from_dict(d.get("character") or {}),
        )


@dataclass
class SettingsConfig:
    monster_dir: str = ""
    hp_pct: int = 50
    mp_pct: int = 50
    attack_range: AttackRange = field(default_factory=AttackRange)
    templates: Templates = field(default_factory=Templates)

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
            attack_range=AttackRange.from_dict(d.get("attack_range") or {}),
            templates=Templates.from_dict(d.get("templates") or {}),
        )