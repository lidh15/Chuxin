import time

import pyautogui as pag

pag.FAILSAFE = False
while True:
    time.sleep(180)
    pag.click(805, 1060)
    time.sleep(0.1)
    pag.click(805, 985)
    time.sleep(0.1)
    pag.click(1157, 354)
    time.sleep(0.5)
    pag.click(1289, 393)
    time.sleep(0.5)
    pag.click(1237, 282)
    time.sleep(0.1)
    pag.click(1127, 209)
