TITLE = 'MapleStory Worlds'


#########################
#       Constants       #
#########################
RESOURCES_DIR = 'resources'

IS_TEST = True


margin_tl = (0, 0)
margin_tr = (0, 0)
#################################
#       Global Variables        #
#################################
# The player's position relative to the minimap
player_pos_ab = (0, 0)
player_name_pos = None

# Describes whether the main bot loop is currently running or not
enabled = False


# Represents the current shortest path that the bot is taking
path = []

appear_other = False

setting_data = None
routine = None



#############################
#       Shared Modules      #
#############################
# A Routine object that manages the 'machine code' of the current routine
routine = None

# Shares the main bot loop
bot = None
input_lock = None
# Shares the video capture loop
capture = None

# Shares the keyboard listener
listener = None

notifier = None
# Shares the gui to all modules
gui = None

macro_thread = None
macro_shutdown_evt = None

SCREEN_WIDTH =  970 # 1366 # 1280,
SCREEN_HEIGHT = 700 # 768 # 720 


# src/common/cleanup.py
from src.common import config

def stop_all_modules():
    # 순서 중요할 때(예: listener → bot → capture → notifier) 조정 가능
    for name in ("listener", "bot", "capture", "notifier"):
        mod = getattr(config, name, None)
        if mod is None:
            continue
        try:
            if hasattr(mod, "stop"):
                mod.stop()
        except Exception as e:
            print(f"[WARN] stop failed for {name}: {e}")
        finally:
            setattr(config, name, None)

    # 실행 상태 플래그도 초기화
    config.enabled = False

