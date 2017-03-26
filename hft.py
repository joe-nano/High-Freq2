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
from pymysql import connect, err, sys, cursors
import queue

# Forex.com currency pair code
ccy_dict={
    'R1': 'EUR/USD',
    'R2': 'GBP/USD',
    'R3': 'USD/JPY',
    'R5': 'EUR/JPY',
    'R8': 'AUD/USD',
    'R9': 'GBP/JPY',
    'R10': 'EUR/CHF',
    'R11': 'USD/CAD',
    'R12': 'EUR/GBP',
    'R13': 'USD/CHF',
    'R14': 'USD/DKK',
    'R15': 'AUD/JPY',
    'R16': 'USD/HKD',
    'R17': 'NZD/USD',
    'R18': 'GBP/AUD',
    'R19': 'EUR/AUD',
    'R20': 'EUR/DKK',
    'R21': 'CAD/JPY',
    'R22': 'AUD/CAD',
    'R23': 'EUR/CAD',
    'R24': 'AUD/NZD',
    'R25': 'GBP/CAD',
    'R26': 'GBP/CHF',
    'R27': 'NZD/JPY',
    'R29': 'CHF/JPY',
    'R30': 'EUR/NZD',
    'R31': 'GBP/NZD',
    'R32': 'USD/NOK',
    'R33': 'USD/SEK',
    'R34': 'USD/SGD',
    'R35': 'AUD/CHF',
    'R36': 'CAD/CHF',
    'R37': 'EUR/NOK',
    'R38': 'EUR/SEK',
    'R39': 'NZD/CAD',
    'R40': 'NZD/CHF',
    'R43': 'SGD/JPY',
    'R46': 'USD/MXN',
    'R47': 'USD/ZAR',
    'R66': 'USD/PLN',
    'R67': 'EUR/PLN',
    'R68': 'USD/TRY',
    'R69': 'EUR/TRY',
    'R70': 'USD/HUF',
    'R71': 'EUR/HUF',
    'R72': 'USD/CZK',
    'R73': 'EUR/CZK',
    'R74': 'ZAR/JPY',
    'R107': 'USD/CNH'
}


def get_boundary(ccy):
    #set threshold to 1.5 pip
    if ('JPY' in ccy)==True:
        lb=0.015
        ub=1
    else:
        lb=0.00015
        ub=1

    return (lb, ub)

def f2o(ccy):

    ccy_pair=ccy.split('/')
    return ccy_pair[0]+'_'+ccy_pair[1]


def o2f(ccy):
    ccy_pair=ccy.split('_')
    return ccy_pair[0]+'/'+ccy_pair[1]



class hft:


    def __init__(self, ccy, trd_enabled, set_obj):
        run_time=time.strftime("%Y%m%d_%H%M%S")
        self.broker1=forexcom(o2f(ccy), set_obj)
        self.broker2=Oanda(ccy, set_obj)
        self.trd_enabled=trd_enabled

        self.ccy=ccy #in XXX_YYY format
        self.locker=threading.Lock()
        self.is_open=None
        self.open_type=''

        self.bd=get_boundary(self.ccy)
        self.last_quote1={'ask':-999999,'bid':-999999}
        self.last_quote2={'ask':-999999,'bid':-999999}
        self.time_stamp1=datetime.datetime(2017, 1, 1, 0, 0, 0, 0)
        self.time_stamp2=datetime.datetime(2017, 1, 1, 0, 0, 0, 0)

        self.num_trade=0
        self.spread_open=0
        self.spread_open_act=0
        self.spread_cum=0

        #configuration
        self.max_amount=set_obj.get_max_amount()
        self.amount=set_obj.get_single_amount()
        self.ping_limit=set_obj.get_ping_limit()

        self.current_amount=0
        self.s=None
        self.stream_queue=queue.Queue()

        self.check_position() #initialize is_open flag/open type, get current amount
        self.connect_db()

    def connect_db(self):

        self.conn_db= connect(host='localhost',
                              user='root',
                              passwd='891124',
                              db='tradingdb')


    def insert_trd_rec(self, trd_rec):

        try:
            cur=self.conn_db.cursor()

            values=''
            key_list=['datetime','ccy','amount','buysell','sprd_open','forex_quote','oanda_quote','fill_price']
            for key in key_list:
                value_tmp=str(trd_rec[key])#.replace(',','/').replace(':','/')
                print (str(key)+' : '+value_tmp)
                values+=value_tmp+','
            values=values[0:-1]

            sql="INSERT INTO fxarb VALUES ("+values+");"

            #print (sql)
            cur.execute(str(sql))
            cur.close()
            self.conn_db.commit()
        except Exception as error:
            if ('ConnectionAbortedError' in str(error))==True:
                print (str(error))
                print ('error encounted, reconnecting...')
                self.connect_db()
                self.insert_trd_rec(trd_rec)

    def print_stream(self):

        while True:
            print (self.stream_queue.get())
            self.stream_queue.task_done()

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
                        if ccy_live_list[0]!='' and ccy_dict[ccy_live_list[0]]==o2f(self.ccy): #not heartbeat

                            self.last_quote1['bid']=float(ccy_live_list[1])
                            self.last_quote1['ask']=float(ccy_live_list[2])
                            self.time_stamp1=datetime.datetime.now()

                            self.locker.acquire()
                            #print (self.ccy, 'Forex.com try to execute...')
                            self.execute()
                            self.stream_queue.put(broker+'('+self.ccy+')'+' '+self.time_stamp1.strftime("%Y-%m-%d %H:%M:%S")+' '+str(self.last_quote1))
                            self.locker.release()
                            #print (broker+' '+datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ccy_live_list)
                except Exception as error:
                    if ('timed' in str(error))==True:
                        print ('Forexcom '+str(self.broker2.ccy)+' connection failed...')
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

                        self.last_quote2['bid']=float(ticks['bids'][0]['price'])
                        self.last_quote2['ask']=float(ticks['asks'][0]['price'])
                        self.time_stamp2=datetime.datetime.now()

                        self.locker.acquire()
                        #print (self.ccy, 'Oanda try to execute...')
                        self.execute()
                        self.stream_queue.put(broker+'('+self.ccy+')'+' '+self.time_stamp2.strftime("%Y-%m-%d %H:%M:%S")+' '+str(self.last_quote2))
                        self.locker.release()
                        #print (broker+' '+datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ticks)
                        
            except Exception as error:
                if ('timed' in str(error))==True or ('Max' in str(error))==True:
                    print ('Oanda '+str(self.broker2.ccy)+' connection failed...')
                    self.broker2.connect()
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
            threads.append(threading.Thread(target=self.print_stream,args=[]))

            for thread in threads:
                thread.start()

        except Exception as error:
            print (self.ccy, 'error encounter in trading, restarting...')
            time.sleep(5)
            self.start()


    def close_position(self):
        self.broker1.close_position()
        self.broker2.close_position()

    def check_position(self):

        broker1_pos_info=self.broker1.get_position()
        broker2_pos_info=self.broker2.get_position()

        #check current open position:
        if broker1_pos_info['units']!=0 and broker2_pos_info['units']!=0: #both account has open position

            if broker1_pos_info['side']=='buy':
                self.current_amount=broker1_pos_info['units']
            else:
                self.current_amount=-broker1_pos_info['units']

        elif broker1_pos_info['units']!=0: #only one account has open position, close it
            self.broker1.close_position()


        elif broker2_pos_info['units']!=0:
            self.broker2.close_position()



    def execute(self):
        try:
            #ask=buy, bid=sell
            trading_time=datetime.datetime.now()
            dt1=trading_time-self.time_stamp1
            dt2=trading_time-self.time_stamp2
            if (self.last_quote2['bid']-self.last_quote1['ask'])>self.bd[0] and (self.last_quote2['bid']-self.last_quote1['ask'])<self.bd[1] and dt1.total_seconds()<self.ping_limit and dt2.total_seconds()<self.ping_limit and self.current_amount<self.max_amount:
                if self.trd_enabled==True:
                    fill_price=self.buy1sell2()
                else:
                    fill_price={'1' : self.last_quote1['bid'], '2': self.last_quote2['ask']}

                if fill_price!=-1:

                    self.spread_open_act=fill_price['2']-fill_price['1']
                    self.spread_cum+=self.spread_open_act
                    self.num_trade+=1
                    self.current_amount+=self.amount #relative to broker1

                    time_now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    trd_rec={
                        'datetime':'\''+time_now+'\'',
                        'ccy':'\''+self.ccy+'\'',
                        'amount':self.amount,
                        'buysell':'\''+'buy Forex.com/sell Oanda'+'\'',
                        'sprd_open':self.spread_open_act,
                        'forex_quote':'\''+str(self.last_quote1).replace('\'','')+'\'',
                        'oanda_quote':'\''+str(self.last_quote2).replace('\'','')+'\'',
                        'fill_price':'\''+str(fill_price).replace('\'','')+'\''
                    }
                    self.insert_trd_rec(trd_rec)
                    print ('cumulative open spread: '+str(self.spread_cum))
                    print (self.ccy, 'current number of trade: '+str(self.num_trade))
                    print ('------------------------------------------------------------')

            elif  (self.last_quote1['bid']-self.last_quote2['ask'])>self.bd[0] and (self.last_quote1['bid']-self.last_quote2['ask'])<self.bd[1] and dt1.total_seconds()<self.ping_limit and dt2.total_seconds()<self.ping_limit and self.current_amount>-self.max_amount:
                if self.trd_enabled==True:
                    fill_price=self.sell1buy2()
                else:
                    fill_price={'1' : self.last_quote1['ask'], '2': self.last_quote2['bid']}

                if fill_price!=-1:

                    self.spread_open_act=fill_price['1']-fill_price['2']
                    self.spread_cum+=self.spread_open_act
                    self.num_trade+=1
                    self.current_amount-=self.amount

                    time_now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    trd_rec={
                        'datetime':'\''+time_now+'\'',
                        'ccy':'\''+self.ccy+'\'',
                        'amount':-self.amount,
                        'buysell':'\''+'sell Forex.com/buy Oanda'+'\'',
                        'sprd_open':self.spread_open_act,
                        'forex_quote':'\''+str(self.last_quote1).replace('\'','')+'\'',
                        'oanda_quote':'\''+str(self.last_quote2).replace('\'','')+'\'',
                        'fill_price':'\''+str(fill_price).replace('\'','')+'\''
                    }
                    self.insert_trd_rec(trd_rec)
                    print ('cumulative open spread: '+str(self.spread_cum))
                    print (self.ccy, 'current number of trade: '+str(self.num_trade))
                    print ('------------------------------------------------------------')

            #print ('heartbeat('+self.ccy+') '+str(datetime.datetime.now())+'...')
        except Exception as error:
            print (self.ccy, 'error encountered, error: '+str(error))

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
                    self.account_num=row[0]
                elif i==4:
                    self.account_token=row[0]
                elif i==5:
                    self.max_amt=row[0]
                elif i==6:
                    self.single_amt=row[0]
                elif i==7:
                    self.ping_limit=row[0]
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

    def get_max_amount(self):
        return int(self.max_amt)

    def get_single_amount(self):
        return int(self.single_amt)

    def get_ping_limit(self):
        return int(self.ping_limit)

def get_hft_list(fileName_, set_obj):
    hft_list=[]
    file = open(fileName_, 'r')
    try:
        reader = csv.reader(file)
        for row in reader:
            if int(row[1])==1:
                ccy=row[0]
                if int(row[2])==1:
                    hft_list.append(hft(ccy, True, set_obj))
                else:
                    hft_list.append(hft(ccy, False, set_obj))
    finally:
        file.close()
    return hft_list



