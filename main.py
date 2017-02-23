import threading
import sys
import time
from ht import *
from datetime import datetime


def main(args):

    weekday=datetime.today().weekday()
    now=datetime.now()

    num_oppo=0

    if False: #(int(weekday)==4 and int(now.hour)>=17) or int(weekday)==5 or (int(weekday)==6 and int(now.hour)<17): #Friday 5pm - Sunday 5pm

        print ('market closed...')
        return None
    else:

        login_file='/Users/MengfeiZhang/Desktop/tmp/login_info_ht.csv'
        #login_file='C:/Users/Mengfei Zhang/Desktop/fly capital/trading/test/login_file_test.csv'

        set_obj=set(login_file)

        #start trading

        ht_obj=ht(set_obj)

        ht_obj.start_live_stream()

        ht_obj.start_trading()


if __name__=='__main__':
    sys.exit(main(sys.argv))