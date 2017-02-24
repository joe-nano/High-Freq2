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

            self.client = oandapyV20.API(access_token=self.token)

            print (self.broker_name+'connection succeeded...')
        except:
            print (self.broker_name+'connection failed...')
            time.sleep(5)
            self.connect()

    def live_stream(self):

        params ={
            "instruments": self.ccy

        }

        req = pricing.PricingStream(accountID=self.account_id, params=params)
        resp_stream = self.client.request(req)
        for ticks in resp_stream:
            if ticks['type']!='HEARTBEAT':
                #print (self.broker_name+datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ticks)
                self.latest_quotes[ticks['instrument']]={'bid':float(ticks['bids'][0]['price']), 'ask':float(ticks['asks'][0]['price'])}



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



    def close_position(self):
        try:

            data ={'longUnits':'ALL'}
            order_close=positions.PositionClose(accountID=self.account_id,instrument=self.ccy,data=data)

            self.client.request(order_close)
            resp_close=order_close.response
            return float(resp_close['longOrderFillTransaction']['price'])

        except Exception as err:

            if ('does not exist' in str(err))==True:
                data ={'shortUnits':'ALL'}
                order_close=positions.PositionClose(accountID=self.account_id,instrument=self.ccy,data=data)

                self.client.request(order_close)
                resp_close=order_close.response
                return float(resp_close['shortOrderFillTransaction']['price'])
            else:
                print ("order not executed "+str(err))

    def get_position(self):


        req_position = positions.OpenPositions(accountID=self.account_id)

        self.client.request(req_position)

        resp_position=req_position.response

        if resp_position['positions']==[]:

            return {'side':'buy','units':0}

        else:
            in_position_list=False
            for pos in resp_position['positions']:

                if pos['instrument']==self.ccy:
                    in_position_list=True
                    net_position=int(pos['short']['units'])+int(pos['long']['units'])

                    if net_position>0:
                        return {'side':'buy','units':abs(net_position)}

                    elif net_position<0:
                        return {'side':'sell','units':abs(net_position)}

            if in_position_list==False:

                return {'side':'buy','units':0}


