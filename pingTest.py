import os
import sys
import time


def main(args):

    hostname = {'api-fxtrade.oanda.com':'oanda'}

    for host in hostname.keys():

        response = os.system("ping -c 3 " + host)

if __name__=='__main__':
    sys.exit(main(sys.argv))