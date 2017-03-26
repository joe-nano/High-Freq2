import threading
import sys
import time
from hft import *
from datetime import datetime


def main(args):


    login_file='/Users/MengfeiZhang/Desktop/tmp/login_info_hft.csv'
    ccy_list_file='/Users/MengfeiZhang/Desktop/tmp/hft_ccy_list.csv'
    #login_file='C:/Users/Mengfei Zhang/Desktop/fly capital/trading/login_info_hft.csv'
    #ccy_list_file='C:/Users/Mengfei Zhang/Desktop/fly capital/trading/hft_ccy_list.csv'

    if sys.argv[1]=='trading':

        set_obj=set(login_file)

        #start trading

        hft_list=get_hft_list(ccy_list_file, set_obj)

        threads=[]

        for hft_obj in hft_list:
            threads.append(threading.Thread(target=hft_obj.start(),args=None))

        for thread in threads:
            thread.start()

    elif sys.argv[1]=='close':

        set_obj=set(login_file)

        #start trading

        ccy_list=['GBP_USD','GBP_JPY'] #list of ccy want to close
        hft_list=[]
        for ccy in ccy_list:
            hft_list.append(hft(ccy, True, set_obj))

        threads=[]

        for hft_obj in hft_list:
            threads.append(threading.Thread(target=hft_obj.close_position(),args=None))

        for thread in threads:
            thread.start()




if __name__=='__main__':
    sys.exit(main(sys.argv))



