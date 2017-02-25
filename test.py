import threading
import sys
from forexcom import *
from Oanda import *
from datetime import datetime
from main import *


login_file='/Users/MengfeiZhang/Desktop/tmp/login_info_ht.csv'

#position_dir='C:/Users/Mengfei Zhang/Desktop/fly capital/trading/test/option_position_test.csv'
#login_file='C:/Users/Mengfei Zhang/Desktop/fly capital/trading/test/login_file_test.csv'

ccy='USD/JPY'

set_obj=set(login_file)

broker1=forexcom('USD/CHF', set_obj)
broker2=Oanda('USD_CHF', set_obj)

print (broker2.get_position())
print (broker1.get_position())
'''

#start trading

hft_obj=hft(ccy, set_obj)

ccy_list=broker1.get_ccy_list()

broker2.ccy_list=ccy_list
broker2.start_live_stream()

time.sleep(15)


while True:

    last_quote1=broker1.get_latest_quotes(ccy)
    last_quote2=broker2.get_latest_quotes(f2o(ccy))

    fill_f=broker1.make_mkt_order(ccy, 1000, 'S')
    fill_o=broker2.make_mkt_order(f2o(ccy), 1000, 'sell')
    if fill_f<=last_quote1['ask']:
        print ('forex good ask')
    else:
        print ('forex bad ask')

    if fill_o<=last_quote2['ask']:
        print ('oanda good ask')
    else:
        print ('oanda bad ask')
    time.sleep(1)

    last_quote1=broker1.get_latest_quotes(ccy)
    last_quote2=broker2.get_latest_quotes(f2o(ccy))

    fill_f=broker1.close_position(ccy)
    fill_o=broker2.close_position(f2o(ccy))

    if fill_f>=last_quote1['bid']:
        print ('forex good bid')
    else:
        print ('forex bad bid')

    if fill_o>=last_quote2['bid']:
        print ('oanda good bid')
    else:
        print ('oanda bad bid')

    time.sleep(1)

def thread_funcA():

    print ('I am outer thread A')

    t1=threading.Thread( target=thread_func2)
    t2=threading.Thread( target=thread_func3)

    t2.start()
    t1.start()


def thread_funcB():

    print ('I am outer thread B')


    t1=threading.Thread( target=thread_func4)
    t2=threading.Thread( target=thread_func5)

    t2.start()
    t1.start()



def thread_func2():

    while 1:
        print ('I am inner thread 1')
        time.sleep(5)

def thread_func3():

    while 1:
        print ('I am inner thread 2')
        time.sleep(5)


def thread_func4():

    while 1:
        print ('I am inner thread 3')
        time.sleep(5)

def thread_func5():

    while 1:
        print ('I am inner thread 4')
        time.sleep(5)


tA=threading.Thread( target=thread_funcA)
tB=threading.Thread( target=thread_funcB)

tA.start()
tB.start()


'''



