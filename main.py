"""The central program that ties all the modules together."""

import time
from src.modules.bot import Bot
from src.modules.capture import Capture
# from src.modules.notifier import Notifier
from src.modules.gui import GUI
from src.modules.listener import Listener
# from src.modules.gui import GUI


bot = Bot()
capture = Capture()
# notifier = Notifier()
listener = Listener()

bot.start()
while not bot.ready:
    time.sleep(0.01)

listener.start()
while not listener.ready:
    time.sleep(0.01)

capture.start()
while not capture.ready:
    time.sleep(0.01)


gui = GUI()
gui.start()

