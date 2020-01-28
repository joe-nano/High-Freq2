import sys
from hft import set
from forexcomv2 import *


def main(args):

    login_file='login_info_hft.csv'
    set_obj=set(login_file)

    forexTrader=forexcom('EUR/JPY', set_obj)

    #lastPx=forexTrader.get_last_price()

    #print(forexTrader.get_nav())
    #print(forexTrader.get_position())

    #last_price={'bid':lastPx-0.00005,'ask':lastPx+0.00005}

    #print(forexTrader.make_mkt_order(15000, 'buy', last_price))

    print(forexTrader.get_market_info('USD/DKK'))


if __name__=='__main__':
    sys.exit(main(sys.argv))