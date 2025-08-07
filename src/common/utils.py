import cv2
import os
import mss
import numpy as np
from src.common import config

def center_from_bounds(top_left, bottom_right):
    """
    top_left: (x1, y1) 튜플 — 영역의 좌상단 좌표
    bottom_right: (x2, y2) 튜플 — 영역의 우하단 좌표
    반환: (cx, cy) 튜플 — 영역의 중심 좌표
    """
    x1, y1 = top_left
    x2, y2 = bottom_right
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    return cx, cy

def single_match(frame, template):
    """
    Finds the best match within FRAME.
    :param frame:       The image in which to search for TEMPLATE.
    :param template:    The template to match with.
    :return:            The top-left and bottom-right positions of the best match.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF) # TM_CCOEFF 방식은 상관계수(Coefficient) 를 이용해, 패턴의 밝기 차이를 보정하며 매칭 점수를 산출
    _, _, _, top_left = cv2.minMaxLoc(result)
    w, h = template.shape[::-1]
    bottom_right = (top_left[0] + w, top_left[1] + h)
    return top_left, bottom_right

def multi_match(frame, template, threshold=0.95):
    """
    Finds all matches in FRAME that are similar to TEMPLATE by at least THRESHOLD.
    :param frame:       The image in which to search.
    :param template:    The template to match with.
    :param threshold:   The minimum percentage of TEMPLATE that each result must match.
    :return:            An array of matches that exceed THRESHOLD.
    """
    if template.shape[0] > frame.shape[0] or template.shape[1] > frame.shape[1]:
        return []
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED) #TM_CCOEFF_NORMED 방식은 TM_CCOEFF 결과를 0~1 사이로 정규화
    locations = np.where(result >= threshold)
    locations = list(zip(*locations[::-1]))
    results = []
    for p in locations:
        x = int(round(p[0] + template.shape[1] / 2))
        y = int(round(p[1] + template.shape[0] / 2))
        results.append((x, y))
    return results

def convert_to_relative(point, frame):
    """
    Converts POINT into relative coordinates in the range [0, 1] based on FRAME.
    Normalizes the units of the vertical axis to equal those of the horizontal
    axis by using config.mm_ratio.
    :param point:   The point in absolute coordinates.
    :param frame:   The image to use as a reference.
    :return:        The given point in relative coordinates.
    """
    x = point[0] / frame.shape[1]
    y = point[1] / config.capture.minimap_ratio / frame.shape[0]
    return x, y
def convert_to_absolute(point, frame):
    """
    Converts POINT into absolute coordinates (in pixels) based on FRAME.
    Normalizes the units of the vertical axis to equal those of the horizontal
    axis by using config.mm_ratio.
    :param point:   The point in relative coordinates.
    :param frame:   The image to use as a reference.
    :return:        The given point in absolute coordinates.
    """

    x = int(round(point[0] * frame.shape[1]))
    y = int(round(point[1] * config.capture.minimap_ratio * frame.shape[0]))
    return x, y


def load_templates(folder):
    temps = []
    for f in os.listdir(folder):
        img = cv2.imread(os.path.join(folder, f), 0)
        if img is None:
            continue
        temps.append(img)
        temps.append(cv2.flip(img, 1))
    
    return temps


def capture_minimap(x1,y1, x2,y2):
        with mss.mss() as sct:
            monitor = {"left": int(x1), "top": int(y1), "width": int(x2 - x1), "height": int(y2 - y1)}
            img = np.array(sct.grab(monitor))[:, :, :3]
            cv2.imwrite("minimap_capture.png", img)


def save_ndarray_as_img(arr: np.ndarray, filepath: str = "capture.png"):
    """
    numpy 배열을 이미지 파일(PNG/JPG 등)로 저장한다.

    Parameters
    ----------
    arr : np.ndarray
        저장할 영상 배열(BGR·BGRA·GRAY 모두 가능).
    filepath : str
        저장 경로와 파일 이름. 확장자에 따라 포맷 결정.
    """
    # ── (선택) float 배열일 경우 0~1 → 0~255 로 변환 ──
    if arr.dtype == np.float32 or arr.dtype == np.float64:
        arr = np.clip(arr * 255, 0, 255).astype(np.uint8)

    # ── (선택) 알파 채널(BGRA) → BGR로 변환 ──
    if arr.shape[2] == 4:                      # BGRA
        arr = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)

    cv2.imwrite(filepath, arr)
    print(f"[INFO] Saved to {filepath}")