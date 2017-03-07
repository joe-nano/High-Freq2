import threading
import sys
import time
from hft import *
from datetime import datetime


def main(args):

    weekday=datetime.today().weekday()
    now=datetime.now()

    if False: #(int(weekday)==4 and int(now.hour)>=17) or int(weekday)==5 or (int(weekday)==6 and int(now.hour)<17): #Friday 5pm - Sunday 5pm

        print ('market closed...')
        return None
    else:

        #login_file='/Users/MengfeiZhang/Desktop/tmp/login_info_ht.csv'
        login_file='C:/Users/Mengfei Zhang/Desktop/fly capital/trading/test/login_info_ht.csv'

        set_obj=set(login_file)

        #start trading

        ccy_list=['USD_JPY','USD_DKK']


        hft_list=[]

        for ccy in ccy_list:
            hft_list.append(hft(ccy, set_obj))


        threads=[]

        for hft_obj in hft_list:
            threads.append(threading.Thread(target=hft_obj.start(),args=None))

        for thread in threads:
            thread.start()


if __name__=='__main__':
    sys.exit(main(sys.argv))