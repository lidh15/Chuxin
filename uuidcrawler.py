import random
import time

from selenium import webdriver
from selenium.webdriver.common.by import By

driver = webdriver.Chrome()
driver.maximize_window()

prefix = '{"source":"majsoul","accountid":15370948,"starttime":1602045496,"endtime":1602046471,"uuid":"'
suffix = '","version":"0.4.5","playerdata":[{"id":15443150,"name":"鈴見奏","rank":2,"pt":78,"finalpoint":22400,"deltapt":-7},{"id":11199262,"name":"baijiajia","rank":4,"pt":411,"finalpoint":24600,"deltapt":10},{"id":15403271,"name":"CCP的銅牆鐵壁","rank":3,"pt":60,"finalpoint":32300,"deltapt":33},{"id":15370948,"name":"数据下载专用","rank":1,"pt":0,"finalpoint":20700,"deltapt":-19}],"roomdata":{"init_point":25000,"fandian":30000,"time_fixed":5,"time_add":20,"dora_count":3,"shiduan":true,"room":1,"player":4,"round":4}}\n'
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
