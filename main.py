import threading
import sys
import time
from hft import *
from datetime import datetime


def main(args):


    #login_file='/Users/MengfeiZhang/Desktop/tmp/login_info_hft.csv'
    #ccy_list_file='/Users/MengfeiZhang/Desktop/tmp/hft_ccy_list.csv'
    login_file='C:/Users/Mengfei Zhang/Desktop/fly capital/trading/login_info_hft.csv'
    ccy_list_file='C:/Users/Mengfei Zhang/Desktop/fly capital/trading/hft_ccy_list.csv'

    if sys.argv[1]=='trading':

        set_obj=set(login_file)

        #start trading

        hft_list=get_hft_list(ccy_list_file, set_obj)

        threads=[]

        #threads.append(threading.Thread(target=safe_check,args=[set_obj])) #check if nav drops too much

        for hft_obj in hft_list:
            threads.append(threading.Thread(target=hft_obj.start(),args=None))

        for thread in threads:
            thread.start()

    elif sys.argv[1]=='close':

        set_obj=set(login_file)

        ccy_list=['EUR_USD','GBP_USD','USD_JPY'] #list of ccy want to close
        hft_list=[]
        for ccy in ccy_list:
            hft_list.append(hft(ccy, True, set_obj))

        threads=[]

        for hft_obj in hft_list:
            threads.append(threading.Thread(target=hft_obj.close_position(),args=None))

        for thread in threads:
            thread.start()

    elif sys.argv[1]=='nav':

        set_obj=set(login_file)

        broker1=forexcom('dummy', set_obj)
        broker2=Oanda('dummy', set_obj)

        while True:
            forexcom_nav=broker1.get_nav()
            oanda_nav=broker2.get_nav()
            print ('Total NAV='+str(oanda_nav+forexcom_nav), 'Forex.com NAV='+str(forexcom_nav), 'Oanda NAV='+str(oanda_nav))
            time.sleep(10)

if __name__=='__main__':
    sys.exit(main(sys.argv))



