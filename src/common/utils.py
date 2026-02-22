import math
import queue
import threading
import cv2
import os
import sys
import mss
import numpy as np
from src.common import config
from tkinter import  messagebox
from random import random
from pathlib import Path
def run_if_enabled(function):
    """
    Decorator for functions that should only run if the bot is enabled.
    :param function:    The function to decorate.
    :return:            The decorated function.
    """

    def helper(*args, **kwargs):
        if config.enabled:
            return function(*args, **kwargs)
    return helper


def run_if_disabled(message=''):
    """
    Decorator for functions that should only run while the bot is disabled. If MESSAGE
    is not empty, it will also print that message if its function attempts to run when
    it is not supposed to.
    """

    def decorator(function):
        def helper(*args, **kwargs):
            if not config.enabled:
                return function(*args, **kwargs)
            elif message:
                print(message)
        return helper
    return decorator

def print_separator():
    """Prints a 3 blank lines for visual clarity."""

    print('\n\n')


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


def filter_color(img, ranges):
    """
    Returns a filtered copy of IMG that only contains pixels within the given RANGES.
    on the HSV scale.
    :param img:     The image to filter.
    :param ranges:  A list of tuples, each of which is a pair upper and lower HSV bounds.
    :return:        A filtered copy of IMG.
    """

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, ranges[0][0], ranges[0][1])
    for i in range(1, len(ranges)):
        mask = cv2.bitwise_or(mask, cv2.inRange(hsv, ranges[i][0], ranges[i][1]))

    # Mask the image
    color_mask = mask > 0
    result = np.zeros_like(img, np.uint8)
    result[color_mask] = img[color_mask]
    return result


def capture_minimap(x1,y1, x2,y2):
        with mss.mss() as sct:
            monitor = {"left": int(x1), "top": int(y1), "width": int(x2 - x1), "height": int(y2 - y1)}
            img = np.array(sct.grab(monitor))[:, :, :3]
            cv2.imwrite("minimap_capture.png", img)


def display_message(title, message):
    messagebox.showinfo(title, message)



##########################
#       Threading        #
##########################
class Async(threading.Thread):
    def __init__(self, function, *args, **kwargs):
        super().__init__()
        self.queue = queue.Queue()
        self.function = function
        self.args = args
        self.kwargs = kwargs

    def run(self):
        self.function(*self.args, **self.kwargs)
        self.queue.put('x')

    def process_queue(self, root):
        def f():
            try:
                self.queue.get_nowait()
            except queue.Empty:
                root.after(100, self.process_queue(root))
        return f
    

def async_callback(context, function, *args, **kwargs):
    """Returns a callback function that can be run asynchronously by the GUI."""

    def f():
        task = Async(function, *args, **kwargs)
        task.start()
        context.after(100, task.process_queue(context))
    return f



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


def load_templates(folder):
    def safe_imread(path, flags=cv2.IMREAD_GRAYSCALE):
        p = Path(path)
        if not p.exists():
            display_message("[ERROR]", f"파일 없음: {p}" )
            return None
        img = imread_u(str(p), flags)
        if img is None:
            display_message("[ERROR]", f"이미지 로드 실패(손상/포맷 문제): {p}" )
        return img
    
    try:
        temps = []
        for f in os.listdir(folder):
            img = safe_imread(os.path.join(folder, f), 0)
            if img is None:
                continue
            temps.append(img)
            temps.append(cv2.flip(img, 1))
        
        return temps
    except:
        display_message('경고', f'{folder}\n는 잘못된 폴더 경로입니다.')




def validate_input(value):
    """
    입력값 타입 및 유효성 검사 함수

    Args:
        value (str|int|float): 검사할 값

    Returns:
        dict: {
            "is_folder": bool,
            "is_image_file": bool,
            "is_number": bool,
            "is_string": bool,
            "valid": bool
        }
    """
    result = {
        "is_folder": False,
        "is_image_file": False,
        "is_number": False,
        "is_string": False,
        "valid": False
    }

    # None 또는 빈값 처리
    if value is None or str(value).strip() == "":
        return result

    # 숫자 여부 체크
    if isinstance(value, (int, float)):
        result["is_number"] = True
        result["valid"] = True
        return result
    
    # 문자열일 경우
    if isinstance(value, str):
        v = value.strip()
        if not v:
            return result

        # Allow both cwd-relative and project/resource-relative paths.
        candidates = []
        for p in (v, resource_path(v)):
            rp = str(Path(p).resolve())
            if rp not in candidates:
                candidates.append(rp)

        # 폴더 경로인지 확인
        for p in candidates:
            if os.path.isdir(p):
                result["is_folder"] = True
                result["valid"] = True
                return result

        # 이미지 파일 경로인지 확인
        for p in candidates:
            if os.path.isfile(p):
                ext = os.path.splitext(p)[1].lower()
                if ext in [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff"]:
                    result["is_image_file"] = True
                    result["valid"] = True
                    return result
        
        # 문자열이 숫자로 변환 가능한지 확인
        try:
            float(value)
            result["is_number"] = True
            result["valid"] = True
            return result
        except ValueError:
            pass

        # 그냥 문자열로 취급
        result["is_string"] = True
        result["valid"] = True
        return result
    
    return result


def imread_u(path: str, flags=cv2.IMREAD_COLOR):
    with open(path, 'rb') as f:
        data = np.frombuffer(f.read(), dtype=np.uint8)
    img = cv2.imdecode(data, flags)
    return img



def bernoulli(p):
    """
    Returns the value of a Bernoulli random variable with probability P.
    :param p:   The random variable's probability of being True.
    :return:    True or False.
    """

    return random() < p


def rand_float(start, end):
    """Returns a random float value in the interval [START, END)."""

    assert start < end, 'START must be less than END'
    return (end - start) * random() + start


def resource_path(relative: str) -> str:
    """
    PyInstaller (--onefile) / 개발 둘 다에서 에셋의 절대경로를 찾아서 반환.
    relative: 'assets/xxx.png' 처럼 프로젝트 루트 기준 상대경로
    """
    # 1) PyInstaller 실행(특히 --onefile)에서는 _MEIPASS에 풀립니다.
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        p = Path(sys._MEIPASS) / relative
        return str(p)

    # 2) 개발환경: 현재 파일에서 위로 올라가며 대상 경로가 존재하는 곳을 탐색
    here = Path(__file__).resolve()
    for base in [here] + list(here.parents):
        cand = base.parent / relative if base.name == 'common' else base / relative
        if cand.exists():
            return str(cand)

    # 3) 마지막으로 현재 작업경로 기준 시도
    return str(Path(relative).resolve())
