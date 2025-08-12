# src/datas/routine_data.py
from dataclasses import dataclass, asdict
from typing import Optional, Literal, List, Dict, Any

ActionType = Literal["move", "jump", "wait", "ladder"]

@dataclass
class ActionItem:
    action: ActionType
    x: int
    y: int
    # 선택 필드 (액션별로 1개만 사용)
    end_y: Optional[int] = None     # ladder 전용
    duration: Optional[int] = None  # wait 전용
    count: Optional[int] = None     # jump 전용

    # ── 유효성 검사 ───────────────────────────────────────────────
    def validate(self) -> None:
        if self.action not in ("move","jump","wait","ladder"):
            raise ValueError("action must be one of move/jump/wait/ladder")
        # 액션별 필드 강제
        if self.action == "ladder":
            if self.end_y is None:
                raise ValueError("ladder requires end_y")
            self.duration = None; self.count = None
        elif self.action == "wait":
            if self.duration is None:
                raise ValueError("wait requires duration")
            self.end_y = None; self.count = None
        elif self.action == "jump":
            if self.count is None:
                raise ValueError("jump requires count")
            self.end_y = None; self.duration = None
        else:  # move
            self.end_y = None; self.duration = None; self.count = None

    # ── 직렬화/역직렬화 ────────────────────────────────────────────
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # None 값은 JSON에 안 넣음(깔끔한 출력)
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ActionItem":
        item = cls(
            action=d["action"],
            x=int(d["x"]),
            y=int(d["y"]),
            end_y=d.get("end_y"),
            duration=d.get("duration"),
            count=d.get("count"),
        )
        item.validate()
        return item

# 리스트 직렬화 도우미
def list_to_jsonable(items: List[ActionItem]) -> List[Dict[str, Any]]:
    return [it.to_dict() for it in items]

def list_from_jsonable(arr: List[Dict[str, Any]]) -> List[ActionItem]:
    return [ActionItem.from_dict(d) for d in arr]
