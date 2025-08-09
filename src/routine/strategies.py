from src.common.vkeys import key_down, key_up
from src.common import config

def step_platformer(direction, target):
    """
    간단한 플랫폼어 이동: 방향키를 아주 짧게 눌러 한 칸씩 미세 이동.
    target은 minimap 좌표 기준으로 쓰이지만, 여기서는 방향만 사용.
    """
    # direction: 'left'/'right'/'up'/'down' 등
    key_down(direction)
    # 환경에 맞춰 튜닝
    # 너무 길면 과도 이동, 너무 짧으면 위치 갱신이 안될 수도 있으니 실험 필요
    import time
    time.sleep(0.035)
    key_up(direction)

def step_grid(direction, target):
    """
    그리드 기반: 타일 하나 정도 이동했다고 가정하는 더 짧은 탭.
"""
    import time
    key_down(direction)
    time.sleep(0.02)
    key_up(direction)

STEP_STRATEGIES = {
    "platformer": step_platformer,
    "grid": step_grid,
}
