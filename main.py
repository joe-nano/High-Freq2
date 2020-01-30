import threading
import sys
import time
from hft import *
from datetime import datetime


def main(args):


    login_file='login_info_hft.csv'
    ccy_list_file='hft_ccy_list.csv'
    nav_file='hft_nav.csv'

    set_obj=set(login_file)

    if sys.argv[1]=='trading':

        #start trading

        hft_list=get_hft_list(ccy_list_file, set_obj)

        threads=[]

        threads.append(threading.Thread(target=monitor,args=[set_obj, nav_file])) #check if nav drops too much

        for hft_obj in hft_list:
            threads.append(threading.Thread(target=hft_obj.start,args=[]))

        for thread in threads:
            thread.start()

    elif sys.argv[1]=='close': #python main.py close USD_JPY

        close(sys.argv[2], set_obj)

    elif sys.argv[1]=='nav':

        broker1=forexcom('USD/JPY', set_obj)
        broker2=Oanda('USD_JPY', set_obj)

        while True:
            forexcom_nav=broker1.get_nav()
            oanda_nav=broker2.get_nav()
            print ('Total NAV='+str(oanda_nav+forexcom_nav), 'Forex.com NAV='+str(forexcom_nav), 'Oanda NAV='+str(oanda_nav))
            print ('Forex position= '+str(broker1.get_position()))
            print ('Oanda position= '+str(broker2.get_position()))
            time.sleep(30)

if __name__=='__main__':
    sys.exit(main(sys.argv))



