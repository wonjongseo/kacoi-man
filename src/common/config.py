TITLE = 'MapleStory Worlds'


#########################
#       Constants       #
#########################
RESOURCES_DIR = 'resources'

IS_TEST = True

#################################
#       Global Variables        #
#################################
# The player's position relative to the minimap
player_pos = (0, 0)
player_pos_ab = (0, 0)
player_name_pos = None

# Describes whether the main bot loop is currently running or not
enabled = False


# Represents the current shortest path that the bot is taking
path = []


setting_data = None
routine = None



#############################
#       Shared Modules      #
#############################
# A Routine object that manages the 'machine code' of the current routine
routine = None

# Shares the main bot loop
bot = None

# Shares the video capture loop
capture = None

# Shares the keyboard listener
listener = None

# Shares the gui to all modules
gui = None