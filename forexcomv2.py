import http.client, urllib.parse
import copy
import xml.etree.ElementTree as ET
import collections
import math
import csv
import datetime
import time
import threading
import smtplib
from email.mime.text import MIMEText
import socket
import sys
import json
import random
import requests
from hftUtil import *


class forexcom:

    def __init__(self, ccy, set_obj):

        self.broker_name='Forex '
        self.set_obj=set_obj
        self.ccy=ccy

        self.username = self.set_obj.get_account_id()
        self.password = self.set_obj.get_account_pwd()

        self.session_id=None
        self.trading_acct_id=402444865 #dev:402448418, #prod: 402444865

        self.base_url='https://ciapi.cityindex.com/TradingAPI/'
        self.connect()

        #initialize
        if self.ccy=='dummy':
            self.market_id=-1
        else:
            self.market_id=self.get_market_info(self.ccy)['MarketId']

    def send_request(self, method, api_url, payload):

        if self.session_id==None:
            headers={'Content-Type': 'application/json'}
        else:
            headers={'Content-Type': 'application/json',
                    'Session': self.session_id,
                    'UserName': self.username
                    }

        full_url = self.base_url + api_url

        req = method + full_url

        try:
            r = requests.request(method, full_url, headers=headers, json=payload)

            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            #print(err)
            #print(r.text)
            None

        #print('request status: ', r.status_code)
        #if r.status_code == 200:

        #printJson(r.json())
        return r.json()

    def connect(self):

        try:
            payload={'UserName': self.username,
                     'Password': self.password}

            resp=self.send_request('POST', 'session', payload)
            if 'Session' in resp:
                print(self.broker_name + self.ccy + ' ' + 'connection succeeded...')
                self.session_id=resp['Session']
                return resp

            else:
                print(self.broker_name + self.ccy + ' ' + 'connection failed: ' + str(resp))
                time.sleep(5)
                self.connect()

        except Exception as error:

            print (self.broker_name+self.ccy+' '+'connection failed: '+str(error))
            time.sleep(5)
            self.connect()


    def get_last_price(self):

        resp = self.send_request('GET', 'market/'+str(self.market_id)+'/tickhistory?PriceTicks=1',{})

        return resp['PriceTicks'][0]['Price']

    def get_market_info(self, ccy):

        resp = self.send_request('GET', 'market/fullsearchwithtags?SearchByMarketName=TRUE&TagId=80&MaxResults=10&Query='+ccy, {})

        for mktInfo in resp['MarketInformation']:

            if mktInfo['Name']==ccy:
                return mktInfo

    def make_limit_order(self, amount, side, prc, last_price):

        payload={"isTrade":False,
                 "AutoRollover":False,
                 "AuditId":"",
                 "Currency":None,
                 "Direction":side,
                 "LastChangedDateTimeUTC":None,
                 "MarketName":self.ccy,
                 "BidPrice":last_price['bid'],
                 "PositionMethodId":1,
                 "ExpiryDateTimeUTCDate":None,
                 "Status":None,
                 "MarketId":self.market_id,
                 "LastChangedDateTimeUTCDate":None,
                 "Reference":None,
                 "OfferPrice":last_price['ask'],
                 "TriggerPrice":prc,
                 "OrderId":0,
                 "Quantity":amount,
                 "QuoteId":None,
                 "IfDone":[],
                 "TradingAccountId":self.trading_acct_id,
                 "OcoOrder":None,
                 "Type":None,
                 "Applicability":"GTC",
                 "ExpiryDateTimeUTC":None
                 }

        resp=self.send_request('POST', 'order/newstoplimitorder', payload)

        if resp['Status'] == 1:
            return resp['Orders'][0]['Price']
        else:
            return -1

    def make_mkt_order(self, amount, side, last_price):

        payload = {"IfDone": [],
                   "Direction": side,
                   "ExpiryDateTimeUTCDate": None,
                   "LastChangedDateTimeUTCDate": None,
                   "OcoOrder": None,
                   "Type": None,
                   "ExpiryDateTimeUTC": None,
                   "Applicability": None,
                   "TriggerPrice": None,
                   "BidPrice": last_price['bid'],
                   "AuditId": "",
                   "AutoRollover": False,
                   "MarketId": self.market_id,
                   "OfferPrice": last_price['ask'],
                   "OrderId": None,
                   "Currency": None,
                   "Quantity": amount,
                   "QuoteId": None,
                   "LastChangedDateTimeUTC": None,
                   "PositionMethodId": 1,
                   "TradingAccountId": self.trading_acct_id,
                   "MarketName": self.ccy,
                   "Status": None,
                   "isTrade": True,
                   "PriceTolerance":100,
                   }

        resp = self.send_request('POST', 'order/newtradeorder', payload)

        if resp['Status'] == 1:
            return resp['Orders'][0]['Price']
        else:
            return -1

    def close_position(self):

        posInfo=self.get_position()

        lastPx=self.get_last_price()

        if posInfo['units']>0:

            if posInfo['side']=='buy':
                close_dir='sell'
            else:
                close_dir='buy'

            payload={"IfDone":[],
                     "Direction":close_dir,
                     "ExpiryDateTimeUTCDate":None,
                     "LastChangedDateTimeUTCDate":None,
                     "OcoOrder":None,
                     "Type":None,
                     "ExpiryDateTimeUTC":None,
                     "Applicability":None,
                     "TriggerPrice":None,
                     "BidPrice": lastPx,
                     "AuditId":"",
                     "AutoRollover":False,
                     "MarketId":self.market_id,
                     "OfferPrice": lastPx,
                     "OrderId":None,
                     "Currency":None,
                     "Quantity":posInfo['units'],
                     "QuoteId":None,
                     "LastChangedDateTimeUTC":None,
                     "PositionMethodId":1,
                     "TradingAccountId":self.trading_acct_id,
                     "MarketName":self.ccy,
                     "Status":None,
                     "isTrade":True
                     }

            resp=self.send_request('POST', 'order/newtradeorder', payload)

            if resp['Status'] == 1:
                return resp['Orders'][0]['Price']
            else:
                return -1

    def get_position(self):

        resp=self.send_request('GET', 'order/openpositions', {'TradingAccountId': self.username})

        pos_dir='buy'
        pos_amount=0
        pos_price=None

        for posInfo in resp['OpenPositions']:
            if posInfo['MarketName']==self.ccy:
                pos_amount+=posInfo['Quantity']
                pos_dir=posInfo['Direction']
                pos_price=posInfo['Price']

        return {'side': pos_dir, 'units': pos_amount, 'price': pos_price}

    def get_nav(self):

        return self.send_request('GET', 'margin/ClientAccountMargin', {})['NetEquity']