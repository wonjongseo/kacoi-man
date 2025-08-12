

import pygetwindow as gw
print(f'gw.getAllTitles : {gw.getAllTitles()}')

windows = gw.getWindowsWithTitle("MapleStory Worlds-Mapleland (빅토리아)")
win =  windows[0]
win.activate()