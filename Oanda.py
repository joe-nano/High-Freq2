import oandapyV20
from oandapyV20 import API
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.pricing as pricing
import oandapyV20.endpoints.positions as positions
import oandapyV20.endpoints.accounts as accounts
import json
import time
import threading
import datetime
import ast
import logging
import urllib.request, urllib.parse

'''
logging.basicConfig(
        filename="/Users/MengfeiZhang/Desktop/tmp/Oanda_v20.log",
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s : %(message)s',
    )
'''
class Oanda:


    def __init__(self, ccy, set_obj):

        self.broker_name='Oanda '
        self.client=None
        self.set_obj=set_obj
        self.ccy=ccy
        self.connect()
        self.latest_quotes={}

    def connect(self):
        try:
            self.account_id=self.set_obj.get_account_num()
            self.token=self.set_obj.get_account_token()
            para={'timeout':30}
            self.client = oandapyV20.API(access_token=self.token, environment='live', request_params=para) #practice, live
            req_acct = accounts.AccountDetails(self.account_id)
            self.client.request(req_acct) #get account info
            print (self.broker_name+self.ccy+' '+'connection succeeded...')
        except Exception as error:
            print (self.broker_name+self.ccy+' '+'connection failed: '+str(error))
            time.sleep(5)
            self.connect()



    def make_mkt_order(self, amount, side):

        order=None
        if side=='buy':

            order={
                    "order": {
                    "instrument": self.ccy,
                    "units": str(amount),
                    "type": "MARKET",
                    "positionFill": "DEFAULT"
                    }
                }

        elif side=='sell':


            order={
                    "order": {
                    "instrument": self.ccy,
                    "units": str(-amount),
                    "type": "MARKET",
                    "positionFill": "DEFAULT"
                    }
                }

        try:
            req = orders.OrderCreate(self.account_id, data=order)
            resp_order=self.client.request(req)

            return float(resp_order['orderFillTransaction']['price'])

        except Exception as err:

            print ("order not executed "+str(err))
            return -1



    def close_position(self):
        try:

            data ={'longUnits':'ALL'}
            order_close=positions.PositionClose(accountID=self.account_id,instrument=self.ccy,data=data)

            self.client.request(order_close)
            resp_close=order_close.response
            return float(resp_close['longOrderFillTransaction']['price'])

        except Exception as err:

            if ('does not exist' in str(err))==True:

                try:
                    data ={'shortUnits':'ALL'}
                    order_close=positions.PositionClose(accountID=self.account_id,instrument=self.ccy,data=data)

                    self.client.request(order_close)
                    resp_close=order_close.response
                    return float(resp_close['shortOrderFillTransaction']['price'])
                except Exception as err:
                    print ("position not closed: "+str(err))
                    return -1

    def get_position(self):

        req_position = positions.OpenPositions(accountID=self.account_id)

        self.client.request(req_position)

        resp_position=req_position.response

        if resp_position['positions']==[]:

            return {'side':'buy','units':0, 'price': None}

        else:
            in_position_list=False
            for pos in resp_position['positions']:

                if pos['instrument']==self.ccy:
                    in_position_list=True
                    net_position=int(pos['short']['units'])+int(pos['long']['units'])

                    if net_position>0:
                        return {'side':'buy','units':abs(net_position), 'price': float(pos['long']['averagePrice'])}

                    elif net_position<0:
                        return {'side':'sell','units':abs(net_position), 'price': float(pos['short']['averagePrice'])}

            if in_position_list==False:

                return {'side':'buy','units':0, 'price': None}

    def get_nav(self):
        try:
            req_acct = accounts.AccountDetails(self.account_id)
            self.client.request(req_acct)
            resp_acct=req_acct.response
            return float(resp_acct['account']['NAV'])
        except Exception as err:

            print('Fail to get Oanda NAV: '+str(err))

    def get_eco_cal(self):

        header={'Authorization':'Bearer '+self.token}

        eco_ccy=['EUR_USD','USD_JPY']
        eco_event=[]
        eco_time={}

        for ccy in eco_ccy:
            url='https://api-fxtrade.oanda.com/labs/v1/calendar?instrument='+ccy+'&period=-604800'
            req=urllib.request.Request(url=url, headers=header, method='GET')
            resp=urllib.request.urlopen(req).read()
            resp=json.loads(resp.decode('utf-8'))

            eco_event+=resp

        for ev in eco_event:
            ev_time=datetime.datetime.fromtimestamp(ev['timestamp'])

            if ev_time.day in eco_time.keys():
                eco_time[ev_time.day].append(ev_time.hour)
            else:
                eco_time[ev_time.day]=[ev_time.hour]

            if ev_time.minute==0:
                eco_time[ev_time.day].append(ev_time.hour-1)

        for key in eco_time:

            eco_time[key]=list(set(eco_time[key]))

        return eco_time