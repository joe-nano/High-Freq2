import oandapyV20
from oandapyV20 import API
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.pricing as pricing
import oandapyV20.endpoints.positions as positions
import json
import time
import threading
import datetime
import ast


def f2o(ccy):

    ccy_pair=ccy.split('/')
    return ccy_pair[0]+'_'+ccy_pair[1]


class Oanda:


    def __init__(self, set_obj):

        self.broker_name='Oanda '
        self.client=None
        self.set_obj=set_obj
        self.ccy_list=None
        self.connect()
        self.latest_quotes={}
        self.show_live_stream=False

    def connect(self):
        try:
            self.account_id=self.set_obj.get_account_num()
            self.token=self.set_obj.get_account_token()

            self.client = oandapyV20.API(access_token=self.token)

            print (self.broker_name+'connection succeeded...')
        except:
            print (self.broker_name+'connection failed...')
            time.sleep(5)
            self.connect()

    def live_stream(self):

        params ={
            "instruments": ','.join(self.ccy_list)

        }

        req = pricing.PricingStream(accountID=self.account_id, params=params)
        resp_stream = self.client.request(req)
        for ticks in resp_stream:
            if ticks['type']!='HEARTBEAT':
                if self.show_live_stream==True:
                    print (self.broker_name+datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ticks)

                self.latest_quotes[ticks['instrument']]={'bid':float(ticks['bids'][0]['price']), 'ask':float(ticks['asks'][0]['price'])}


    def start_live_stream(self):
        print (self.broker_name+'start steaming...')
        threading.Thread(target = self.live_stream).start()

    def get_latest_quotes(self, ccy):

        #print (self.broker_name+'latest quotes',ccy, self.latest_quotes[ccy], datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        return self.latest_quotes[ccy]


    def make_mkt_order(self, ccy, amount, side):

        order=None
        if side=='buy':

            order={
                "order": {
                "instrument": ccy,
                "units": str(amount),
                "type": "MARKET",
                "positionFill": "DEFAULT"
                }
                }

        elif side=='sell':


            order={
                "order": {
                "instrument": ccy,
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



    def close_position(self, ccy):
        try:

            data ={'longUnits':'ALL'}
            order_close=positions.PositionClose(accountID=self.account_id,instrument=ccy,data=data)

            self.client.request(order_close)
            resp_close=order_close.response
            return float(resp_close['longOrderFillTransaction']['price'])

        except Exception as err:

            if ('does not exist' in str(err))==True:
                data ={'shortUnits':'ALL'}
                order_close=positions.PositionClose(accountID=self.account_id,instrument=ccy,data=data)

                self.client.request(order_close)
                resp_close=order_close.response
                return float(resp_close['shortOrderFillTransaction']['price'])
            else:
                print ("order not executed "+str(err))

    def get_position(self, ccy):


        req_position = positions.OpenPositions(accountID=self.account_id)

        self.client.request(req_position)

        resp_position=req_position.response

        print (resp_position)
        if resp_position['positions']==[]:

            return {'side':'buy','units':0}

        else:
            in_position_list=False
            for pos in resp_position['positions']:

                if pos['instrument']==ccy:
                    in_position_list=True
                    net_position=int(pos['short']['units'])+int(pos['long']['units'])

                    if net_position>0:
                        return {'side':'buy','units':abs(net_position)}

                    elif net_position<0:
                        return {'side':'sell','units':abs(net_position)}

            if in_position_list==False:

                return {'side':'buy','units':0}


