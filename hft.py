import http.client, urllib.parse
import copy
import xml.etree.ElementTree as ET
import collections
import math
import csv
import datetime
import time
import threading
import smtplib
from email.mime.text import MIMEText
import socket
import sys
import json
import oandapyV20
from oandapyV20 import API
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.pricing as pricing
import oandapyV20.endpoints.positions as positions
import ast
from forexcom import *
from Oanda import *


def get_boundary(ccy):

    if ('JPY' in ccy)==True:
        lb=0.005
        ub=0.1
    else:
        lb=0.0001
        ub=0.1

    return (lb, ub)

def f2o(ccy):

    ccy_pair=ccy.split('/')
    return ccy_pair[0]+'_'+ccy_pair[1]


def o2f(ccy):
    ccy_pair=ccy.split('_')
    return ccy_pair[0]+'/'+ccy_pair[1]


class hft:


    def __init__(self, ccy, set_obj):
        run_time=time.strftime("%Y%m%d_%H%M%S")
        self.broker1=forexcom(o2f(ccy), set_obj)
        self.broker2=Oanda(ccy, set_obj)
        log_dir='C:/Users/Mengfei Zhang/Desktop/fly capital/trading/test/hft log'
        #log_dir='/Users/MengfeiZhang/Desktop/tmp'

        self.ccy=ccy #in XXX_YYY format
        self.locker=threading.Lock()
        self.is_open=None
        self.open_type=''

        self.bd=get_boundary(self.ccy)
        self.last_quote1={'ask':-999999,'bid':-999999}
        self.last_quote2={'ask':-999999,'bid':-999999}


        self.num_trade=0
        self.spread_open=0
        self.spread_open_act=0

        self.max_amount=10000
        self.current_amount=0
        self.amount=1000

        self.s=None
        self.f=open(log_dir+'/'+self.ccy+'_hft_log_'+run_time+'.txt','w')

        self.check_position() #initialize is_open flag/open type, get current amount

    def trading(self, broker):


        if broker=='Forexcom':

            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.settimeout(30)
            self.s.connect((self.broker1.rates_conn_info['IP'], int(self.broker1.rates_conn_info['Port'])))
            self.s.sendall(bytes(self.broker1.token, 'utf-8'))


            while True:
                try:
                    data_tmp=self.s.recv(1024).decode("utf-8")
                    ccy_list_tmp=data_tmp.split('\r')
                    for ccy in ccy_list_tmp:
                        ccy_live_list=ccy.split('\\')
                        if ccy_live_list[0]!='': #not heart beat
                            self.last_quote1['bid']=float(ccy_live_list[1])
                            self.last_quote1['ask']=float(ccy_live_list[2])

                            if ccy_dict[ccy_live_list[0]]==o2f(self.ccy):
                                self.locker.acquire(True)
                                #print (self.ccy, 'Forex.com try to execute...')
                                self.execute()
                                self.locker.release()

                    #print (broker+' '+datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), data_tmp)

                except Exception as error:
                    if ('timed' in str(error))==True:
                        self.broker1.connect()
                        self.trading('Forexcom')

        elif broker=='Oanda':

            params ={
                "instruments": self.broker2.ccy,
            }

            try:
                req = pricing.PricingStream(accountID=self.broker2.account_id, params=params)
                resp_stream = self.broker2.client.request(req)
                for ticks in resp_stream:
                    if ticks['type']!='HEARTBEAT':

                        #print (broker+' '+datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ticks)

                        self.last_quote2['bid']=float(ticks['bids'][0]['price'])
                        self.last_quote2['ask']=float(ticks['asks'][0]['price'])

                        self.locker.acquire(True)
                        #print (self.ccy, 'Oanda try to execute...')
                        self.execute()
                        self.locker.release()

            except Exception as error:
                if ('timed' in str(error))==True or ('Max' in str(error))==True:
                    print ('Oanda '+str(self.broker2.ccy)+' connection failed...')
                    time.sleep(5)
                    self.trading('Oanda')

        else:

            print ('unknwon broker...')
            return None

    def start(self):
        try:
            print (self.ccy+' started...')
            threads=[]
            threads.append(threading.Thread(target=self.trading,args=['Forexcom']))
            threads.append(threading.Thread(target=self.trading,args=['Oanda']))

            for thread in threads:
                thread.start()

        except Exception as error:
            print (self.ccy, 'error encounter in trading, restarting...')
            time.sleep(5)
            self.start()


    def check_position(self):

        broker1_pos_info=self.broker1.get_position()
        broker2_pos_info=self.broker2.get_position()

        #check current open position:
        if broker1_pos_info['units']!=0 and broker2_pos_info['units']!=0: #both account has open position

            if broker1_pos_info['side']=='buy':
                self.current_amount=broker1_pos_info['units']
            else:
                self.current_amount=-broker1_pos_info['units']

            #self.spread_open_act=abs(broker1_pos_info['price']-broker2_pos_info['price']) #assume existing spread > 0

        elif broker1_pos_info['units']!=0: #only one account has open position, close it
            self.broker1.close_position()


        elif broker2_pos_info['units']!=0:
            self.broker2.close_position()

            #self.is_open=False


    def execute(self):
        try:
            print ('test print: '+str(self.num_trade), file=self.f)
            #ask=buy, bid=sell
            if (self.last_quote2['bid']-self.last_quote1['ask'])>self.bd[0] and (self.last_quote2['bid']-self.last_quote1['ask'])<self.bd[1] and self.current_amount<self.max_amount:
                fill_price=self.buy1sell2()

                if fill_price!=-1:

                    self.spread_open_act=fill_price['2']-fill_price['1']
                    self.num_trade+=1
                    self.current_amount+=self.amount #relative to broker1

                    time_now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print (self.ccy+' trading triggered '+str(time_now)+'...')
                    print (self.ccy+': buy Forex.com sell Oanda', file=self.f)
                    print ('current total amount: '+str(self.current_amount), file=self.f)
                    print ('actual open spread: '+str(self.spread_open_act), file=self.f)
                    print (self.last_quote1, file=self.f)
                    print (self.last_quote2, file=self.f)
                    print ('filled price: '+str(fill_price), file=self.f)
                    print ('total number of trade: '+str(self.num_trade), file=self.f)
                    print (time_now, file=self.f)
                    print ('------------------------------------------------------------', file=self.f)

            elif  (self.last_quote1['bid']-self.last_quote2['ask'])>self.bd[0] and (self.last_quote1['bid']-self.last_quote2['ask'])<self.bd[1] and self.current_amount>-self.max_amount:
                fill_price=self.sell1buy2()

                if fill_price!=-1:

                    self.spread_open_act=fill_price['1']-fill_price['2']
                    self.num_trade+=1
                    self.current_amount-=self.amount

                    time_now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print (self.ccy+' trading triggered '+str(time_now)+'...')
                    print (self.ccy+': buy Oanda sell Forex.com', file=self.f)
                    print ('current total amount: '+str(self.current_amount), file=self.f)
                    print ('actual open spread: '+str(self.spread_open_act), file=self.f)
                    print (self.last_quote1, file=self.f)
                    print (self.last_quote2, file=self.f)
                    print ('filled price: '+str(fill_price), file=self.f)
                    print ('total numer of trade: '+str(self.num_trade), file=self.f)
                    print (time_now, file=self.f)
                    print ('------------------------------------------------------------', file=self.f)

            #print ('heartbeat('+self.ccy+') '+str(datetime.datetime.now())+'...')
        except Exception as error:
            print (self.ccy, 'error encountered, trading not executed, error: '+str(error))

    def buy1sell2(self):
        fill_price_buy=self.broker1.make_limit_order(self.amount, 'B', self.last_quote1['ask'])
        if fill_price_buy>0:
            fill_price_sell=self.broker2.make_mkt_order(self.amount, 'sell')

            return {'1' : fill_price_buy, '2': fill_price_sell}

        else:

            return -1

    def sell1buy2(self):
        fill_price_sell=self.broker1.make_limit_order(self.amount, 'S', self.last_quote1['bid'])
        if fill_price_sell>0:
            fill_price_buy=self.broker2.make_mkt_order(self.amount, 'buy')

            return {'1' : fill_price_sell, '2': fill_price_buy}

        else:

            return -1



class set:
    def __init__(self, login_file):

        file = open(login_file, 'r')
        i=1
        try:
            reader = csv.reader(file)
            for row in reader:
                if i==1:
                    self.account_id=row[0]
                elif i==2:
                    self.account_pwd=row[0]
                elif i==3:
                    self.email_login=row[0]
                elif i==4:
                    self.email_pwd=row[0]
                elif i==5:
                    self.account_num=row[0]
                elif i==6:
                    self.account_token=row[0]
                i+=1

        finally:
            file.close()

    def get_account_num(self):
        return self.account_num

    def get_account_token(self):
        return self.account_token

    def get_account_id(self):
        return str(self.account_id)

    def get_account_pwd(self):
        return str(self.account_pwd)

    def get_email_login(self):
        return str(self.email_login)

    def get_email_pwd(self):
        return str(self.email_pwd)


def send_hotmail(subject, content, set_obj):
    msg_txt=format_email_dict(content)
    from_email={'login': set_obj.get_email_login(), 'pwd': set_obj.get_email_pwd()}
    to_email='finatos@me.com'

    msg=MIMEText(msg_txt)
    msg['Subject'] = subject
    msg['From'] = from_email['login']
    msg['To'] = to_email
    mail=smtplib.SMTP('smtp.live.com',25)
    mail.ehlo()
    mail.starttls()
    mail.login(from_email['login'], from_email['pwd'])
    mail.sendmail(from_email['login'], to_email, msg.as_string())
    mail.close()


def format_email_dict(content):
    content_tmp=''
    for item in content.keys():
        content_tmp+=str(item)+':'+str(content[item])+'\r\n'
    return content_tmp