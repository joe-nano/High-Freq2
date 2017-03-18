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
sys.setrecursionlimit(99999999)


def datecov2(date):
    date=str(date)
    return date[0:4]+date[5:7]+date[8:10]




# Forex.com currency pair code
ccy_dict={'R20': 'EUR/DKK',
          'R17': 'NZD/USD',
          'R47': 'USD/ZAR',
          'R29': 'CHF/JPY',
          'R13': 'USD/CHF',
          'R30': 'EUR/NZD',
          'R25': 'GBP/CAD',
          'R107': 'USD/CNH',
          'R68': 'USD/TRY',
          'R67': 'EUR/PLN',
          'R36': 'CAD/CHF',
          'R23': 'USD/HKD',
          'R26': 'GBP/CHF',
          'R71': 'EUR/HUF',
          'R70': 'USD/HUF',
          'R22': 'AUD/CAD',
          'R15': 'AUD/JPY',
          'R39': 'NZD/CAD',
          'R72': 'USD/CZK',
          'R73': 'EUR/CZK',
          'R32': 'USD/NOK',
          'R21': 'CAD/JPY',
          'R34': 'USD/SGD',
          'R10': 'EUR/CHF',
          'R3': 'USD/JPY',
          'R69': 'EUR/TRY',
          'R19': 'EUR/AUD',
          'R35': 'AUD/CHF',
          'R2': 'GBP/USD',
          'R24': 'AUD/NZD',
          'R8': 'AUD/USD',
          'R14': 'GBP/AUD',
          'R9': 'GBP/JPY',
          'R66': 'USD/PLN',
          'R31': 'GBP/NZD',
          'R40': 'NZD/CHF',
          'R43': 'SGD/JPY',
          'R16': 'EUR/CAD',
          'R46': 'USD/MXN',
          'R11': 'USD/CAD',
          'R33': 'USD/SEK',
          'R12': 'EUR/GBP',
          'R27': 'NZD/JPY',
          'R5': 'EUR/JPY',
          'R18': 'USD/DKK',
          'R1': 'EUR/USD',
          'R74': 'ZAR/JPY',
          'R37': 'EUR/NOK',
          'R38': 'EUR/SEK',
          'R4': 'XAU/USD',
          'R28':'XAG/USD'}

class XmlListConfig(list):
    def __init__(self, aList):
        for element in aList:
            if len(element)!=0:
                # treat like dict
                if len(element) == 1 or element[0].tag != element[1].tag:
                    self.append(XmlDictConfig(element))
                # treat like list
                elif element[0].tag == element[1].tag:
                    self.append(XmlListConfig(element))
            elif element.text:
                text = element.text.strip()
                if text:
                    self.append(text)

class XmlDictConfig(dict):

    def __init__(self, parent_element):
        if parent_element.items():
            self.update(dict(parent_element.items()))
        for element in parent_element:
            if len(element)!=0:
                # treat like dict - we assume that if the first two tags
                # in a series are different, then they are all different.
                if len(element) == 1 or element[0].tag != element[1].tag:
                    aDict = XmlDictConfig(element)
                # treat like list - we assume that if the first two tags
                # in a series are the same, then the rest are the same.
                else:
                    # here, we put the list in dictionary; the key is the
                    # tag name the list elements all share in common, and
                    # the value is the list itself
                    aDict = {element[0].tag: XmlListConfig(element)}
                # if the tag has attributes, add those to the dict
                if element.items():
                    aDict.update(dict(element.items()))
                self.update({element.tag: aDict})
            # this assumes that if you've got an attribute in a tag,
            # you won't be having any text. This may or may not be a
            # good idea -- time will tell. It works for the way we are
            # currently doing XML configuration files...
            elif element.items():
                self.update({element.tag: dict(element.items())})
            # finally, if there are no child tags and no attributes, extract
            # the text
            else:
                self.update({element.tag: element.text})


def xml2dict(resp_xml_str):

    pfx=["""xmlns="www.GainCapital.com.WebServices" """, """xmlns="www.GainCapital.com.WebServices/" """]

    for p in pfx:
        p_tmp=p.replace(" ","")
        resp_xml_str=resp_xml_str.replace(p_tmp,'')

    resp_xml_str=resp_xml_str.replace('\\r\\n','').replace('b\'','').replace('\'','')
    #print (resp_xml_str) #for debug
    root=ET.fromstring(resp_xml_str)
    xmldict = XmlDictConfig(root)
    return xmldict

class forexcom:

    def __init__(self, ccy, set_obj):

        self.broker_name='Forex '
        self.token=None
        self.set_obj=set_obj
        self.ccy=ccy



        self.header_aut={
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': 'www.GainCapital.com.WebServices/AuthenticateCredentials'
            }

        self.header_cfg={
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': 'www.GainCapital.com.WebServices/GetConfigurationSettings'

        }

        self.header_lmt_ord={
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': 'www.GainCapital.com.WebServices/DealRequest'

        }

        self.header_close_pos={
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': 'www.GainCapital.com.WebServices/ClosePosition'

        }

        self.header_get_pos={
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': 'www.GainCapital.com.WebServices/GetPositionBlotterWithFilter'

        }


        self.req_soap_aut="""<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
          <soap:Header>
            <Authenticator xmlns="www.GainCapital.com.WebServices">
              <ApplicationName>FlyCapital</ApplicationName>
            </Authenticator>
          </soap:Header>
          <soap:Body>
            <AuthenticateCredentials xmlns="www.GainCapital.com.WebServices">
              <userID>{username}</userID>
              <password>{password}</password>
            </AuthenticateCredentials>
          </soap:Body>
        </soap:Envelope>"""

        self.req_soap_cfg="""<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
          <soap:Header>
            <Authenticator xmlns="www.GainCapital.com.WebServices">
              <ApplicationName>FlyCapital</ApplicationName>
            </Authenticator>
          </soap:Header>
          <soap:Body>
            <GetConfigurationSettings xmlns="www.GainCapital.com.WebServices">
              <Token>{token}</Token>
            </GetConfigurationSettings>
          </soap:Body>
        </soap:Envelope>"""

        self.req_soap_lmt_ord="""<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
          <soap:Header>
            <Authenticator xmlns="www.GainCapital.com.WebServices">
              <ApplicationName>FlyCapital</ApplicationName>
            </Authenticator>
          </soap:Header>
          <soap:Body>
            <DealRequest xmlns="www.GainCapital.com.WebServices">
              <Token>{token}</Token>
              <Product>{ccy}</Product>
              <BuySell>{buysell}</BuySell>
              <Amount>{amount}</Amount>
              <Rate>{rate}</Rate>
            </DealRequest>
          </soap:Body>
        </soap:Envelope>"""

        self.req_soap_close_pos="""<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
          <soap:Header>
            <Authenticator xmlns="www.GainCapital.com.WebServices">
              <ApplicationName>FlyCapital</ApplicationName>
            </Authenticator>
          </soap:Header>
          <soap:Body>
            <ClosePosition xmlns="www.GainCapital.com.WebServices">
              <Token>{token}</Token>
              <Product>{ccy}</Product>
            </ClosePosition>
          </soap:Body>
        </soap:Envelope>"""

        self.req_soap_get_pos="""<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
          <soap:Header>
            <Authenticator xmlns="www.GainCapital.com.WebServices">
              <ApplicationName>FlyCapital</ApplicationName>
            </Authenticator>
          </soap:Header>
          <soap:Body>
            <GetPositionBlotterWithFilter xmlns="www.GainCapital.com.WebServices">
              <Token>{token}</Token>
              <Product>{ccy}</Product>
            </GetPositionBlotterWithFilter>
          </soap:Body>
        </soap:Envelope>"""

        # connect
        self.connect()

    def connect(self):

        try:

            conn = http.client.HTTPConnection('demoweb.efxnow.com',timeout=10)
            conn.request('POST', '/gaincapitalwebservices/authenticate/authenticationservice.asmx', self.req_soap_aut.format(username=self.set_obj.get_account_id(), password=self.set_obj.get_account_pwd()), self.header_aut)
            resp = str(conn.getresponse().read())

            resp_dict=xml2dict(resp)['{http://schemas.xmlsoap.org/soap/envelope/}Body']['AuthenticateCredentialsResponse']['AuthenticationResult']
            if resp_dict['success']=='true':
                print (self.broker_name+self.ccy+' '+'connection succeeded...')
                self.token=resp_dict['token']

                conn = http.client.HTTPConnection('demoweb.efxnow.com',timeout=10)
                conn.request('POST', '/GainCapitalWebServices/Configuration/ConfigurationService.asmx', self.req_soap_cfg.format(token=self.token), self.header_cfg)
                resp = str(conn.getresponse().read())
                resp_dict=xml2dict(resp)['{http://schemas.xmlsoap.org/soap/envelope/}Body']['GetConfigurationSettingsResponse']['GetConfigurationSettingsResult']
                if resp_dict['Success']=='true':

                    self.rates_conn_info = resp_dict['RatesConnection']['Connection'][0] #take the first IP and Port

                else:
                    print (self.broker_name+'unable to get configuration settings...')
                    return None
            else:
                print (self.broker_name+self.ccy+' '+'connection failed...')
                time.sleep(5)
                self.connect()
        except Exception as error:

            print (self.broker_name+self.ccy+' '+'connection failed...')
            print (error)
            time.sleep(5)
            self.connect()


    '''
    def make_mkt_order(self, amount, side):
        req=urllib.parse.urlencode({'Token': self.token,
                            'Product': self.ccy,
                            'BuySell':side,
                            'Amount': amount})

        conn = http.client.HTTPConnection('demoweb.efxnow.com',timeout=10)
        conn.request('POST', '/gaincapitalwebservices/trading/tradingservice.asmx/DealRequestAtBest', req, headers)
        resp = str(conn.getresponse().read())
        resp_dict=xml2dict(resp)

        return float(resp_dict['rate'])
    '''

    def make_limit_order(self, amount, side, prc):

        conn = http.client.HTTPConnection('demoweb.efxnow.com',timeout=10)
        conn.request('POST', '/gaincapitalwebservices/trading/tradingservice.asmx', self.req_soap_lmt_ord.format(token=self.token, ccy=self.ccy, buysell=side, amount=amount, rate=prc), self.header_lmt_ord)
        resp = str(conn.getresponse().read())
        resp_dict=xml2dict(resp)['{http://schemas.xmlsoap.org/soap/envelope/}Body']['DealRequestResponse']['DealRequestResult']

        if resp_dict['success']=='true':
            return float(resp_dict['rate'])
        else:
            return -1

    def close_position(self):

        conn = http.client.HTTPConnection('demoweb.efxnow.com',timeout=10)
        conn.request('POST', '/gaincapitalwebservices/trading/tradingservice.asmx', self.req_soap_close_pos.format(token=self.token, ccy=self.ccy), self.header_close_pos)
        resp = str(conn.getresponse().read())
        resp_dict=xml2dict(resp)['{http://schemas.xmlsoap.org/soap/envelope/}Body']['ClosePositionResponse']['ClosePositionResult']

        return float(resp_dict['rate'])

    def get_position(self):

        conn = http.client.HTTPConnection('demoweb.efxnow.com',timeout=10)
        conn.request('POST', '/gaincapitalwebservices/trading/tradingservice.asmx', self.req_soap_get_pos.format(token=self.token, ccy=self.ccy), self.header_get_pos)
        resp = str(conn.getresponse().read())
        resp_dict=xml2dict(resp)['{http://schemas.xmlsoap.org/soap/envelope/}Body']['GetPositionBlotterWithFilterResponse']['GetPositionBlotterWithFilterResult']
        if resp_dict['Success']=='true':
            try:
                position=int(resp_dict['Output']['Position']['Contract'])
                if position!=0:
                    position_dict={}

                    position_dict['units']=abs(position)
                    position_dict['price']=float(resp_dict['Output']['Position']['AverageRate'])
                    if position>0:
                        position_dict['side']='buy'
                    else:
                        position_dict['side']='sell'

                    return position_dict

                else:
                    return {'side':'buy','units':0, 'price': None}
            except:
                return {'side':'buy','units':'N/A', 'price': None} #cannot get contract info
        else:
            print ('invalid product...')