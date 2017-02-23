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

#start trading

broker1=forexcom(set_obj)
broker2=Oanda(set_obj)


print (broker2.get_position('EUR_JPY'))
'''
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
'''