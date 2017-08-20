import threading
import sys
from forexcom import *
from Oanda import *
from datetime import datetime
from main import *
import pymysql
from pymysql import connect, err, sys, cursors



def insert_trd_rec(conn, dict):

    cur=conn.cursor()

    values=''
    key_list=['datetime','ccy','amount','buysell','sprd_open','forex_quote','oanda_quote','fill_price','profit']
    for key in key_list:
        values+=str(dict[key])+','
    values=values[0:-1]

    sql="INSERT INTO fxarb VALUES ("+values+");"

    print (sql)
    cur.execute(str(sql))

    print(cur.description)
    for row in cur:
        print (row)

    cur.close()
    conn.commit()



def main(args):

    login_file='/Users/MengfeiZhang/Desktop/tmp/login_info_hft.csv'
    ccy_list_file='/Users/MengfeiZhang/Desktop/tmp/hft_ccy_list.csv'
    #login_file='C:/Users/Mengfei Zhang/Desktop/fly capital/trading/login_info_hft.csv'
    #ccy_list_file='C:/Users/Mengfei Zhang/Desktop/fly capital/trading/hft_ccy_list.csv'

    set_obj=set(login_file)

    '''
    conn= connect(host='localhost',
                      user='root',
                      passwd='891124',
                      db='tradingdb')
    dict={
        'datetime':'\'2017-08-09\'',
        'ccy':'\'EUR_USD\'',
        'amount':1000,
        'buysell':'\'buy oanda/sell forex.com\'',
        'sprd_open':0.0005,
        'forex_quote':'\'bid/121/ask/122\'',
        'oanda_quote':'\'bid/120/ask/120.5\'',
        'fill_price':'\'1/122/2/120.5\'',
        'profit':123.314135141341413413414
    }

    insert_trd_rec(conn,dict)
    '''

    trd_time=datetime(2017, 8, 21, 3, 0, 0, 0)
    broker2=Oanda('dummy', set_obj)
    trd_hour=broker2.get_eco_cal()
    print (trd_hour)

    print (in_trd_hour(trd_time, trd_hour))

if __name__=='__main__':
    sys.exit(main(sys.argv))








