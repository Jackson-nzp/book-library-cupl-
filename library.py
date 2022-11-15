import requests
import json
import re
import time
import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from icecream import ic
from retry import retry

import pandas as pd
#由于需要登陆校园网才能抢座，部署到服务器后，如何实现代理配置


#该登录函数利用客户端的cookie信息完成登录，首次使用需要手动登录并获取cookie
#domain cookie 记得每日更新，以免过expire date
def login(num,pwd,domain_cookie):
    #调用webdriver 忽略证书ssl错误
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--ignore-ssl-errors')
    driver=webdriver.Chrome(options=chrome_options)

    #登录
    driver.get('http://libseat.cupl.edu.cn/#/ic/home')
    time.sleep(1)#避免响应过快打不开
    #Xpath获取输入元素，不使用post是因为有加密
    name = driver.find_element(by=By.XPATH, value='//*[@id="app"]/div[1]/div[5]/div/div[1]/form/div[1]/div/div[1]/input')
    name.send_keys(num)    #输入学号
    password = driver.find_element(by=By.XPATH, value='//*[@id="app"]/div[1]/div[5]/div/div[1]/form/div[2]/div/div[1]/input')
    password.send_keys(pwd)    #输入密码
    login = driver.find_element(by=By.XPATH, value='//*[@id="app"]/div[1]/div[5]/div/div[1]/form/div[3]/div/button')
    login.click()   #点击登录按钮

    #为预约座位调用api获取信息
    userinfo = driver.execute_script('return sessionStorage.getItem("userInfo");')#观察可知token存储位置
    userinfo=userinfo.split(',')
    token=userinfo[29].split(":")[1]
    print(token) 
    cookies=[]
    lib_cookies = driver.get_cookies()
    cookies=domain_cookie+lib_cookies[0].get('value')
    #webdriver的add_cookie太不好用
    #之所以需要和domain结合主要是有多个域，下一步可以考虑使用代理截获。
    #明天试试能否不用domain呢？
    return token,cookies
#webdriver不会自动结束，故还可以继续使用token和cookie，且由于使用文件存储需要手动更新，应该不会过时。
def reserve(token,cookies,ide,seat,tor_date):
    '''
    domain_cookie=domain_cookie.split(';')
    for cookie in domain_cookie:
        driver.get('http://libseat.cupl.edu.cn/#/ic/home')
        time.sleep(1)
        dict_cookie={
            'domain':'.cupl.edu.cn',
            'name':cookie.split('=')[0],
            'value':cookie.split('=')[1]
        }
        driver.add_cookie(dict_cookie)
    driver.get('http://libseat.cupl.edu.cn/#/ic/home')
    print(driver.get_cookies())
    
    cookies=driver.add_cookie(lib_cookies)
    print(cookies)
    '''
    header = {
        "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36',
        'Connection': 'keep-alive',
        'Origin': 'http://libseat.cupl.edu.cn',
        'Referer': 'http://libseat.cupl.edu.cn/',
        'token':str(token),
        'Cookie':cookies
    }
    
    reserve_api = 'http://libseat.cupl.edu.cn/ic-web/reserve'
    res_param = {
            "sysKind":8,
            "appAccNo":ide,
            "memberKind":1,
            "resvMember":[ide],
            "resvBeginTime":str(tor_date)+" 09:00:00",
            "resvEndTime":str(tor_date)+" 22:00:00",
            "testName":"",
            "captcha":"",
            "resvProperty":0,
            "resvDev":[seat],
            "memo":""
    }
    #此处必须要开启对话么，反正我直接用webdriver存续期内的cookie构造也可以把，nmd，得补一补这方面知识了
    session = requests.session()
    res = session.post(url=reserve_api, headers=header, json=res_param)
    tmp = json.loads(res.content)
    return tmp

def main():
    cur_time = time.strftime("%H:%M:%S", time.localtime())
    print(cur_time)
    flag = True
    while cur_time < '21:39:00':
        if flag is True:
            print('当前时段暂不可预约')
            flag = False
        cur_time = time.strftime("%H:%M:%S", time.localtime())
    cur_date = datetime.date.today()
    tor_date = cur_date + datetime.timedelta(days=1)
    tor_date = str(tor_date)

    #从文件中获取身份信息
    person=pd.read_csv('D:\\01 学习资料\\00 研究\\04 计算机\\01 工作储备\\02 语言\\02 python\\03 爬虫\\00 项目\\01 图书馆抢座位\identity.csv')
    seats=pd.read_csv('D:\\01 学习资料\\00 研究\\04 计算机\\01 工作储备\\02 语言\\02 python\\03 爬虫\\00 项目\\01 图书馆抢座位\seats.csv')
    for i in range(person.shape[0]):
        num=person.iloc[i][0]
        pwd=person.iloc[i][1]
        domain_cookie=person.iloc[i][3]
        #如果要抢座位，做好还是能同时操作多人，如何实现多线程
        token,cookies=login(num,pwd,domain_cookie)
        print(token,cookies)
        #获取座位信息，之所以不选择迭代是因为座位有区分，靠近窗口等，故不做尝试。
        ide=person.iloc[i][2]
        for i in range(seats.shape[0]):
            seat=seats.iloc[i][1]
            tmp=reserve(token,cookies,ide,seat,tor_date)
            #此处是对异常处理，如果是未到约定时间，继续申请该值，如果是已被占用或其他非法，申请下一个
            if tmp=='':
                print(1)



if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    print('耗时：%.2fs' % (end_time - start_time))
