import copy
import math
import csv
import datetime
import time
import threading
import smtplib
import sys, os
import json
import http.client, urllib.parse
from email.mime.text import MIMEText

import oandapyV20.endpoints.pricing as pricing
from forexcomv2 import *
from Oanda import *
from pymysql import connect, err, sys, cursors
import queue

from lightstreamer_client import LightstreamerClient
from lightstreamer_client import LightstreamerSubscription

MAX_TRD_TIME=10
MAX_NEG_TRD=5
SAFE_BUFFER=60
TRD_BUFFER=60
RESTART_TIME=3600
TRD_HOUR=range(0,24)
TRD_RESET_HOUR=0
UPPER_BOUND=1


def get_boundary(ccy):

    if 'JPY' in ccy:
        scal=100.0
        lb=1.0
        ub=scal
    else:
        scal=10000.0
        lb=1.0
        ub=scal
    return (lb/scal, ub/scal, scal)

def f2o(ccy):

    ccy_pair=ccy.split('/')
    return ccy_pair[0]+'_'+ccy_pair[1]


def o2f(ccy):
    ccy_pair=ccy.split('_')
    return ccy_pair[0]+'/'+ccy_pair[1]


class hft:


    def __init__(self, ccy, trd_enabled, set_obj):
        self.broker1=forexcom(o2f(ccy), set_obj)
        self.broker2=Oanda(ccy, set_obj)
        self.trd_enabled=trd_enabled
        self.set_obj=set_obj

        self.ccy=ccy #in XXX_YYY format
        self.locker=threading.Lock()
        self.run=True

        self.bd=get_boundary(self.ccy)
        self.last_quote1={'ask':-999999,'bid':-999999}
        self.last_quote2={'ask':-1,'bid':-1}
        self.time_stamp1=datetime.datetime(2017, 1, 1, 0, 0, 0, 0)
        self.time_stamp2=datetime.datetime(2017, 1, 1, 0, 0, 0, 0)
        self.trd_buffer_time=datetime.datetime(2017, 1, 1, 0, 0, 0, 0)
        self.safe_buffer_time=datetime.datetime(2017, 1, 1, 0, 0, 0, 0)
        self.stream_queue=queue.Queue()

        #configuration
        self.max_amount=set_obj.get_max_amount()
        self.amount=set_obj.get_single_amount() #min amount
        self.latency_limit=set_obj.get_latency_limit()
        self.neg_tol=MAX_NEG_TRD
        self.safe_buffer=SAFE_BUFFER #seconds
        self.trd_buffer=TRD_BUFFER #seconds
        self.trd_hour=TRD_HOUR

        self.num_neg_spread=0
        self.spread_open_act=0
        self.trd_amount=0
        self.trd_time=1
        self.current_amount=0
        self.profit=0

        self.check_position() #initialize is_open flag/open type, get current amount
        self.connect_db() #<-- True=dev testing

    def connect_db(self, local=False):

        if local == True:
            self.conn_db = connect(host='localhost',
                              user='root',
                              passwd='FN891124mysql',
                              db='tradingdb')

        else:

            self.conn_db = connect(host='mysqlaws.cwdlc79zzkjv.us-east-2.rds.amazonaws.com',
                              user='mysqlaws',
                              passwd='FN891124mysqlaws',
                              db='tradingdb')


    def insert_trd_rec(self, trd_rec):

        try:
            cur=self.conn_db.cursor()

            values=''
            key_list=['datetime','ccy','amount','buysell','sprd_open','ib_quote','oanda_quote','fill_price','profit']
            for key in key_list:
                value_tmp=str(trd_rec[key])#.replace(',','/').replace(':','/')
                #print (str(key)+' : '+value_tmp)
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

    def quotesHandler(self, ls_data):
        self.last_quote1['bid'] = float(ls_data['values']['Bid'])
        self.last_quote1['ask'] = float(ls_data['values']['Offer'])
        self.time_stamp1 = datetime.datetime.now()

        if (self.time_stamp1 - self.trd_buffer_time).total_seconds() > self.trd_buffer and \
                (self.time_stamp1 - self.safe_buffer_time).total_seconds() > self.safe_buffer:
            self.locker.acquire()
            self.execute()
            self.locker.release()
        self.stream_queue.put('Forexcom (' + self.ccy + ')' + ' ' + self.time_stamp1.strftime("%Y-%m-%d %H:%M:%S") + ' ' + str(self.last_quote1))

    def trading(self, broker):

        try:

            if broker=='Forexcom':

                self.ls_client = LightstreamerClient(self.broker1.username, self.broker1.session_id,"https://push.cityindex.com", "STREAMINGALL")

                try:
                    self.ls_client.connect()
                except Exception as e:
                    print("Unable to connect to Lightstreamer Server", e)

                subscription = LightstreamerSubscription(adapter="PRICES", mode="MERGE", items=["PRICE."+str(self.broker1.market_id)], fields=["Bid", "Offer"])
                subscription.addlistener(self.quotesHandler)

                self.ls_client.subscribe(subscription)

                while True:
                    if self.run==False:
                        self.ls_client.disconnect()
                        return None


            elif broker=='Oanda':

                params ={
                    "instruments": self.broker2.ccy,
                }

                req = pricing.PricingStream(accountID=self.broker2.account_id, params=params)
                resp_stream = self.broker2.client.request(req)
                for ticks in resp_stream:
                    if self.run==True:

                        if ticks['type']!='HEARTBEAT':

                            self.last_quote2['bid']=float(ticks['bids'][0]['price'])
                            self.last_quote2['ask']=float(ticks['asks'][0]['price'])
                            self.time_stamp2=datetime.datetime.now()
                            if self.time_stamp2.hour==TRD_RESET_HOUR: #reset daily trade limit
                                self.trd_time=0

                            if (self.time_stamp2-self.trd_buffer_time).total_seconds()>self.trd_buffer and \
                                    (self.time_stamp2-self.safe_buffer_time).total_seconds()>self.safe_buffer: #only call execute when resume==True
                                self.locker.acquire()
                                self.execute()
                                self.locker.release()

                            self.stream_queue.put(broker+'('+self.ccy+')'+' '+self.time_stamp2.strftime("%Y-%m-%d %H:%M:%S")+' '+str(self.last_quote2))
                    else:
                        return None

            else:

                print ('unknwon broker...')
                return None

        except Exception as error:

            try:
                self.locker.release()
            except Exception as lckErr:
                None

            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            if broker == 'Forexcom':
                self.ls_client.disconnect() #disconnect first
                self.broker1.connect()
            elif broker=='Oanda':
                self.broker2.connect()

            print(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")) +' '+ broker + ' trading failed: ' + str(error))
            print('restarting '+broker+' ...')
            time.sleep(30)
            self.trading(broker)

    '''
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
    
    '''
    def start(self):

        print(self.ccy + ' started...')
        printThread=threading.Thread(target=self.print_stream, args=[])
        printThread.start()

        while True:

            self.run=True

            threads=[]
            threads.append(threading.Thread(target=self.trading,args=['Forexcom']))
            threads.append(threading.Thread(target=self.trading,args=['Oanda']))

            for thread in threads:
                thread.start()

            time.sleep(RESTART_TIME)

            self.run=False

            for thread in threads:
                thread.join()

            print(datetime.datetime.now(), self.ccy+' scheduled restarting...')


    def close_position(self):
        self.broker1.close_position()
        self.broker2.close_position()

    def check_position(self):

        broker1_pos_info=self.broker1.get_position()
        broker2_pos_info=self.broker2.get_position()

        #check current open position:
        if broker1_pos_info['units']==broker2_pos_info['units']: #if amount are the same in two accounts

            if broker1_pos_info['side']=='buy':
                self.current_amount=broker1_pos_info['units']
            else:
                self.current_amount=-broker1_pos_info['units']

        else: #if amount are not the same in two account close all
            if broker2_pos_info['units']==0:
                self.broker1.close_position()
            elif broker1_pos_info['units']==0:
                self.broker2.close_position()
            else:
                self.close_position()

            send_hotmail('Unbalanced position ('+self.ccy+'):', {'msg':' Position closed out'}, self.set_obj)


    def get_trd_amount(self, sprd, dir):
        '''
        avl_amount=0

        if dir=='1': #buy more forex.com
            avl_amount=self.max_amount-self.current_amount
        elif dir=='2': #buy more Oanda
            avl_amount=self.current_amount+self.max_amount
        '''

        self.trd_amount=self.amount

    def execute(self):
        try:
            #ask=buy, bid=sell
            last_quote1_snap = copy.deepcopy(self.last_quote1)
            last_quote2_snap = copy.deepcopy(self.last_quote2)

            trading_time=datetime.datetime.now()
            dt1=trading_time-self.time_stamp1
            dt2=trading_time-self.time_stamp2

            if self.trd_time<=MAX_TRD_TIME \
                    and (trading_time.hour in self.trd_hour) \
                    and (last_quote2_snap['bid']-last_quote1_snap['ask'])>=self.bd[0] \
                    and abs(last_quote2_snap['bid']-last_quote1_snap['ask'])<self.bd[1] \
                    and max(dt1.total_seconds(), dt2.total_seconds())<self.latency_limit \
                    and self.current_amount<self.max_amount:

                self.get_trd_amount(last_quote2_snap['bid']-last_quote1_snap['ask'], '1') #calculate trade amount

                if self.trd_amount!=0: #if it is zero, then no need to trade

                    if self.trd_enabled==True:
                        fill_price=self.buy1sell2()
                    else:
                        fill_price={'1' : last_quote1_snap['ask'], '2': last_quote2_snap['bid']}

                    if fill_price!=-1:

                        if self.ccy[-3:]=='USD':
                            self.spread_open_act=fill_price['2']-fill_price['1']
                        else:
                            self.spread_open_act=(fill_price['2']-fill_price['1'])/((fill_price['1'] + fill_price['2']) / 2)

                        self.current_amount+=self.trd_amount #relative to broker1
                        self.profit=self.spread_open_act*self.trd_amount-self.trd_amount*0.000095
                        self.trd_time+=1

                        time_now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                        trd_rec={
                            'datetime':'\''+time_now+'\'',
                            'ccy':'\''+self.ccy+'\'',
                            'amount':self.trd_amount,
                            'buysell':'\''+'buy Forex.com/sell Oanda'+'\'',
                            'sprd_open':self.spread_open_act,
                            'forex_quote':'\''+str(last_quote1_snap).replace('\'','')+'\'',
                            'oanda_quote':'\''+str(last_quote2_snap).replace('\'','')+'\'',
                            'fill_price':'\''+str(fill_price).replace('\'','')+'\'',
                            'profit':self.profit
                        }
                        self.insert_trd_rec(trd_rec)
                        send_hotmail('Position opened ('+self.ccy+')', trd_rec, self.set_obj)


                        if self.spread_open_act<0:
                            self.num_neg_spread+=1
                            if self.num_neg_spread>=self.neg_tol:
                                self.safe_buffer_time = datetime.datetime.now()
                        else:
                            self.trd_buffer_time = datetime.datetime.now()
                            self.num_neg_spread=0


            elif  self.trd_time<=MAX_TRD_TIME \
                    and (trading_time.hour in self.trd_hour) \
                    and (last_quote1_snap['bid']-last_quote2_snap['ask'])>=self.bd[0] \
                    and abs(last_quote1_snap['bid']-last_quote2_snap['ask'])<self.bd[1] \
                    and max(dt1.total_seconds(), dt2.total_seconds())<self.latency_limit \
                    and self.current_amount>-self.max_amount:

                self.get_trd_amount(last_quote1_snap['bid']-last_quote2_snap['ask'], '2') #calculate trade amount

                if self.trd_amount!=0: #if it is zero, then no need to trade

                    if self.trd_enabled==True:
                        fill_price=self.sell1buy2()
                    else:
                        fill_price={'1' : last_quote1_snap['bid'], '2': last_quote2_snap['ask']}

                    if fill_price!=-1:

                        if self.ccy[-3:]=='USD':
                            self.spread_open_act=fill_price['1']-fill_price['2']
                        else:
                            self.spread_open_act=(fill_price['1']-fill_price['2'])/((fill_price['1'] + fill_price['2']) / 2)
                        self.current_amount-=self.trd_amount
                        self.profit=self.spread_open_act*self.trd_amount-self.trd_amount*0.000095
                        self.trd_time+=1

                        time_now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        trd_rec={
                            'datetime':'\''+time_now+'\'',
                            'ccy':'\''+self.ccy+'\'',
                            'amount':-self.trd_amount,
                            'buysell':'\''+'sell Forex.com/buy Oanda'+'\'',
                            'sprd_open':self.spread_open_act,
                            'forex_quote':'\''+str(last_quote1_snap).replace('\'','')+'\'',
                            'oanda_quote':'\''+str(last_quote2_snap).replace('\'','')+'\'',
                            'fill_price':'\''+str(fill_price).replace('\'','')+'\'',
                            'profit':self.profit
                        }
                        self.insert_trd_rec(trd_rec)
                        send_hotmail('Position opened ('+self.ccy+')', trd_rec, self.set_obj)

                        if self.spread_open_act<0:
                            self.num_neg_spread+=1
                            if self.num_neg_spread>=self.neg_tol:

                                self.safe_buffer_time=datetime.datetime.now()
                        else:
                            self.trd_buffer_time = datetime.datetime.now()
                            self.num_neg_spread=0


        except Exception as error:
            print (self.ccy, 'error encountered, error: '+str(error))


    def buy1sell2(self):
        fill_price_sell = self.broker2.make_fok_order(self.trd_amount, 'sell', self.last_quote2['bid'])
        if fill_price_sell>0:
            fill_price_buy = self.broker1.make_mkt_order(self.trd_amount, 'buy', self.last_quote1)
            if fill_price_buy>0:
                return {'1' : fill_price_buy, '2': fill_price_sell}
            else:
                self.close_position()
                send_hotmail('Execution error ('+self.ccy+'):', {'msg':'Oanda not executed'}, self.set_obj)
                return -1
        else:
            return -1

    def sell1buy2(self):
        fill_price_buy = self.broker2.make_fok_order(self.trd_amount, 'buy', self.last_quote2['ask'])
        if fill_price_buy>0:
            fill_price_sell = self.broker1.make_mkt_order(self.trd_amount, 'sell', self.last_quote1)
            if fill_price_sell>0:
                return {'1' : fill_price_sell, '2': fill_price_buy}
            else:
                self.close_position()
                send_hotmail('Execution error ('+self.ccy+'):', {'msg':'Oanda not executed'}, self.set_obj)
                return -1
        else:
            return -1

    '''
    def buy1sell2(self):
        fill_price_buy=self.broker1.make_mkt_order(self.trd_amount, 'buy', self.last_quote1)
        if fill_price_buy>0:
            fill_price_sell=self.broker2.make_mkt_order(self.trd_amount, 'sell')
            if fill_price_sell>0:
                return {'1' : fill_price_buy, '2': fill_price_sell}
            else:
                self.close_position()
                send_hotmail('Execution error ('+self.ccy+'):', {'msg':'Oanda not executed'}, self.set_obj)
                return -1
        else:
            return -1

    def sell1buy2(self):
        fill_price_sell=self.broker1.make_mkt_order(self.trd_amount, 'sell', self.last_quote1)
        if fill_price_sell>0:
            fill_price_buy=self.broker2.make_mkt_order(self.trd_amount, 'buy')
            if fill_price_buy>0:
                return {'1' : fill_price_sell, '2': fill_price_buy}
            else:
                self.close_position()
                send_hotmail('Execution error ('+self.ccy+'):', {'msg':'Oanda not executed'}, self.set_obj)
                return -1
        else:
            return -1
    '''


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
                    self.email_login=row[0]
                elif i==6:
                    self.email_pwd=row[0]
                elif i==7:
                    self.max_amt=row[0]
                elif i==8:
                    self.single_amt=row[0]
                elif i==9:
                    self.latency_limit=row[0]
                elif i==10:
                    self.max_loss=row[0]
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

    def get_max_amount(self):
        return int(self.max_amt)

    def get_single_amount(self):
        return int(self.single_amt)

    def get_latency_limit(self):
        return int(self.latency_limit)

    def get_max_loss(self):
        return float(self.max_loss)


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

def close(ccy, set_obj):

    hft_obj=hft(ccy, True, set_obj)
    hft_obj.close_position()


def monitor(set_obj, nav_path):
    print ('Monitor started...')
    broker1=forexcom('dummy', set_obj)
    broker2=Oanda('dummy', set_obj)
    timer=60*5
    time_cum=0

    init_nav=broker1.get_nav()+broker2.get_nav()
    prev_nav=init_nav
    while True:
        try:
            current_nav=broker1.get_nav()+broker2.get_nav()
            #print ('current NAV: '+str(current_nav)) #for debugging
            time_cum+=timer

            weekday=datetime.datetime.today().weekday()
            now=datetime.datetime.now()

            if current_nav-init_nav>-set_obj.get_max_loss():
                if time_cum>=3600: #check every hour
                    init_nav=current_nav
                    time_cum=0

                    if int(now.hour)==15: #if 3 pm
                        nav_file=open(nav_path,'a')
                        writer=csv.writer(nav_file)
                        writer.writerow([str(now.strftime("%Y%m%d_%H%M%S")), current_nav])

                prev_nav=current_nav
                time.sleep(timer)
            else:
                if current_nav-prev_nav<-set_obj.get_max_loss():
                    send_hotmail('Loss exceeds max limit', {'msg':'All threads stopped'}, set_obj)
                    os._exit(0) #if loss>max loss limit exit the entire program
                else: # withdraw
                    init_nav=current_nav

        except:
            time.sleep(5)
            monitor(set_obj, nav_path)


def send_hotmail(subject, content, set_obj):
    msg_txt=format_email_dict(content)
    from_email={'login': set_obj.get_email_login(), 'pwd': set_obj.get_email_pwd()}
    to_email='finatos@me.com'

    msg=MIMEText(msg_txt)
    msg['Subject'] = subject
    msg['From'] = from_email['login']
    msg['To'] = to_email
    mail=smtplib.SMTP('smtp.live.com',587)
    mail.ehlo()
    mail.starttls()
    mail.login(from_email['login'], from_email['pwd'])
    mail.sendmail(from_email['login'], to_email, msg.as_string())
    mail.close()


def format_email_dict(content):

    return json.dumps(content,indent=2)