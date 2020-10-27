import random
import time

from selenium import webdriver
from selenium.webdriver.common.by import By

driver = webdriver.Chrome()
driver.maximize_window()

'''You need a real data as a hook for the crawler like this
youraccountid = ''
yourname = ''
prefix = '{"source":"majsoul","accountid":%s,"starttime":0,"endtime":0,"uuid":"'%youraccountid
suffix = '","version":"0.4.5","playerdata":[{"id":0,"name":"","rank":0,"pt":0,"finalpoint":25000,"deltapt":0},{"id":0,"name":"","rank":0,"pt":0,"finalpoint":25000,"deltapt":0},{"id":0,"name":"","rank":0,"pt":0,"finalpoint":25000,"deltapt":0},{"id":%s,"name":"%s","rank":0,"pt":0,"finalpoint":25000,"deltapt":0}],"roomdata":{"init_point":25000,"fandian":30000,"time_fixed":5,"time_add":20,"dora_count":3,"shiduan":true,"room":1,"player":4,"round":4}}\n'%(youraccountid, yourname)
'''
prefix = ''
suffix = ''
for month in range(1, 10):
    for date in range(1, 30):
        output = []
        driver.get('https://saki.sapk.ch/2020-%02d-%02d'%(month, date))
        time.sleep(5)
        for pos in range(600, 140600, 1400):
            try:
                screen = []
                driver.execute_script("var q=document.documentElement.scrollTop=%d"%pos)
                time.sleep(2)
                # rows = driver.find_elements(By.CLASS_NAME, 'ReactVirtualized__Table__row')
                rows = driver.find_elements(By.CLASS_NAME, 'player.font-weight-bold.false')
                for row in rows:
                    # rowid = int(row.get_attribute('aria-rowindex'))
                    uuid = row.find_element_by_tag_name('a').get_attribute('href').split('=')[1].split('_')[0]
                    if not uuid in output:
                        screen.append(uuid)
                output.extend(screen)
            except:
                with open('uuidcrawler.log', 'a') as logFile:
                    logFile.writelines(['crawl failed on %d, %02d-%02d\n'%(pos, month, date)])
            finally:
                pass
        with open('gamedata.txt', 'a') as outputFile:
            outputFile.writelines([prefix+uuid+suffix for uuid in output])
with open('gamedata.txt', 'a') as outputFile:
    outputFile.writelines([prefix+'201007-d6fc1cfd-e518-4892-a875-662f09c66b5b'+suffix])
driver.close()
