from forexcom import *
from Oanda import *

def get_boundary(ccy):

    if ('JPY' in ccy)==True:
        lb=0.005
        ub=0.1
    else:
        lb=0.0001
        ub=0.1

    return (lb, ub)


class ht:


    def __init__(self, set_obj):

        self.broker1=forexcom(set_obj)
        self.broker2=Oanda(set_obj)
        self.ccy_list=None
        self.locker=threading.Lock()
        self.spread_open={}
        self.spread_open_act={}
        self.open_type={}


    def start_live_stream(self):

        self.broker1.start_live_stream()

        time.sleep(15)

        self.ccy_list=self.broker1.get_ccy_list()
        #self.ccy_list=['GBP/JPY'] # for test a purticular pair

        self.broker2.ccy_list=self.ccy_list
        self.broker2.start_live_stream()

        time.sleep(15)


    def start_trading(self):
        self.num_oppo=0

        threads=[]
        for ccy in self.ccy_list:
            threads.append(threading.Thread(target=self.trading,args=[ccy]))

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()



    def trading(self, ccy):
        self.locker.acquire(True)
        print (ccy+' started...')
        self.locker.release()
        bd=get_boundary(ccy)
        amount=5000
        threshold=0.33
        timer=0.1
        profit=0

        try:
            #check current open position:
            if self.broker1.get_position(ccy)['units']!=0 and self.broker2.get_position(ccy)['units']!=0: #both account has open position
                is_open=True
            elif self.broker1.get_position(ccy)['units']==0 and self.broker2.get_position(ccy)['units']==0: #both account has no open position
                is_open=False
            else: #one account has open position
                if self.broker1.get_position(ccy)['units']!=0:
                    self.broker1.close_position(ccy)
                elif self.broker2.get_position(ccy)['units']!=0:
                    self.broker2.close_position(ccy)

                is_open=False

            while 1:

                if is_open==False: #does not have open position

                    last_quote1=self.broker1.get_latest_quotes(ccy)
                    last_quote2=self.broker2.get_latest_quotes(f2o(ccy))

                    #ask=buy, bid=sell
                    if (last_quote2['bid']-last_quote1['ask'])>bd[0] and (last_quote2['bid']-last_quote1['ask'])<bd[1]:

                        fill_price_buy=self.broker1.make_limit_order(ccy, amount, 'B', last_quote1['ask'])
                        if fill_price_buy>0:
                            fill_price_sell=self.broker2.make_mkt_order(f2o(ccy), amount, 'sell')


                            self.spread_open_act[ccy]=fill_price_sell-fill_price_buy

                            if self.spread_open_act[ccy]<=0:
                                fill_price_sell=self.broker1.close_position(ccy)
                                fill_price_buy=self.broker2.close_position(f2o(ccy))
                                profit+=self.spread_open_act[ccy]-(fill_price_buy-fill_price_sell)

                                self.locker.acquire(True)
                                print (ccy, 'open with negative spread, position closed...')
                                print ('actual profit: '+str(self.spread_open_act[ccy]-(fill_price_buy-fill_price_sell)))
                                print ('current total profit: '+str(profit))
                                print ('------------------------------------------------------------')
                                self.locker.release()
                            else:
                                self.num_oppo+=1
                                is_open=True
                                self.open_type[ccy]='1a2b'
                                self.spread_open[ccy]=last_quote2['bid']-last_quote1['ask']

                                self.locker.acquire(True)
                                print (ccy, 'open position: 1a<2b')
                                print ('target open spread: '+str(self.spread_open[ccy]))
                                print ('actual open spread: '+str(self.spread_open_act[ccy]))
                                print (last_quote1)
                                print (last_quote2)
                                print ('filled price: ', {'buy1': fill_price_buy, 'sell2':fill_price_sell})
                                print ('current total opportunity: '+str(self.num_oppo))
                                print (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                                print ('------------------------------------------------------------')
                                self.locker.release()
                                #time.sleep(10)
                    elif  (last_quote1['bid']-last_quote2['ask'])>bd[0] and (last_quote1['bid']-last_quote2['ask'])<bd[1]:

                        fill_price_sell=self.broker1.make_limit_order(ccy, amount, 'S', last_quote1['bid'])
                        if fill_price_sell>0:
                            fill_price_buy=self.broker2.make_mkt_order(f2o(ccy), amount, 'buy')

                            self.spread_open_act[ccy]=fill_price_sell-fill_price_buy

                            if self.spread_open_act[ccy]<=0:
                                fill_price_buy=self.broker1.close_position(ccy)
                                fill_price_sell=self.broker2.close_position(f2o(ccy))
                                profit+=self.spread_open_act[ccy]-(fill_price_buy-fill_price_sell)

                                self.locker.acquire(True)
                                print (ccy, 'open with negative spread, position closed...')
                                print ('actual profit: '+str(self.spread_open_act[ccy]-(fill_price_buy-fill_price_sell)))
                                print ('current total profit: '+str(profit))
                                print ('------------------------------------------------------------')
                                self.locker.release()
                            else:
                                self.open_type[ccy]='2a1b'
                                is_open=True
                                self.num_oppo+=1
                                self.spread_open[ccy]=last_quote1['bid']-last_quote2['ask']

                                self.locker.acquire(True)
                                print (ccy, 'open position: 2a<1b')
                                print ('target open spread: '+str(self.spread_open[ccy]))
                                print ('actual open spread: '+str(self.spread_open_act[ccy]))
                                print (last_quote1)
                                print (last_quote2)
                                print ('filled price: ', {'buy2': fill_price_buy, 'sell1':fill_price_sell})
                                print ('current total opportunity: '+str(self.num_oppo))
                                print (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                                print ('------------------------------------------------------------')
                                self.locker.release()
                                #time.sleep(10)
                else: #has open position

                    if self.open_type[ccy]=='1a2b':

                        last_quote1=self.broker1.get_latest_quotes(ccy)
                        last_quote2=self.broker2.get_latest_quotes(f2o(ccy))
                        spread_close=-(last_quote1['bid']-last_quote2['ask'])
                        if spread_close<self.spread_open_act[ccy]*threshold:

                            fill_price_sell=self.broker1.make_limit_order(ccy, amount, 'S', last_quote1['bid'])
                            if fill_price_sell>0:
                                fill_price_buy=self.broker2.make_mkt_order(f2o(ccy), amount, 'buy')

                                is_open=False
                                profit+=self.spread_open_act[ccy]-(fill_price_buy-fill_price_sell)
                                self.locker.acquire(True)
                                print (ccy, 'close position...')
                                print ('target close spread: '+str(spread_close))
                                print ('actual close spread: '+str(fill_price_buy-fill_price_sell))
                                print ('target profit: '+str(self.spread_open[ccy]-spread_close))
                                print ('actual profit: '+str(self.spread_open_act[ccy]-(fill_price_buy-fill_price_sell)))
                                print ('current total profit: '+str(profit))
                                print (last_quote1)
                                print (last_quote2)
                                print ('filled price: ', {'buy2': fill_price_buy, 'sell1':fill_price_sell})
                                print (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                                print ('------------------------------------------------------------')
                                self.locker.release()

                    elif self.open_type[ccy]=='2a1b':
                        last_quote1=self.broker1.get_latest_quotes(ccy)
                        last_quote2=self.broker2.get_latest_quotes(f2o(ccy))
                        spread_close=-(last_quote1['ask']-last_quote2['bid'])
                        if spread_close<self.spread_open_act[ccy]*threshold:

                            fill_price_buy=self.broker1.make_limit_order(ccy, amount, 'B', last_quote1['ask'])
                            if fill_price_buy>0:
                                fill_price_sell=self.broker2.make_mkt_order(f2o(ccy), amount, 'sell')

                                is_open=False
                                profit+=self.spread_open_act[ccy]-(fill_price_buy-fill_price_sell)
                                self.locker.acquire(True)
                                print (ccy, 'close position...')
                                print ('target close spread: '+str(spread_close))
                                print ('actual close spread: '+str(fill_price_buy-fill_price_sell))
                                print ('target profit: '+str(self.spread_open[ccy]-spread_close))
                                print ('actual profit: '+str(self.spread_open_act[ccy]-(fill_price_buy-fill_price_sell)))
                                print ('current total profit: '+str(profit))
                                print (last_quote1)
                                print (last_quote2)
                                print ('filled price: ', {'buy1': fill_price_buy, 'sell2':fill_price_sell})
                                print (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                                print ('------------------------------------------------------------')
                                self.locker.release()
                    else:

                        print ('unknown open type...')


                time.sleep(timer)
        except Exception as error:
            print (ccy, 'error encountered: '+str(error))
            print (ccy, 'restarting...')
            self.trading(ccy)



class set:
    def __init__(self, login_file):

        file = open(login_file, 'r')
        i=1
        try:
            reader = csv.reader(file)
            for row in reader:
                if i==1:
                    self.account_id=row[0]
                elif i==2:
                    self.account_pwd=row[0]
                elif i==3:
                    self.email_login=row[0]
                elif i==4:
                    self.email_pwd=row[0]
                elif i==5:
                    self.account_num=row[0]
                elif i==6:
                    self.account_token=row[0]
                i+=1

        finally:
            file.close()

    def get_account_num(self):
        return self.account_num

    def get_account_token(self):
        return self.account_token

    def get_account_id(self):
        return str(self.account_id)

    def get_account_pwd(self):
        return str(self.account_pwd)

    def get_email_login(self):
        return str(self.email_login)

    def get_email_pwd(self):
        return str(self.email_pwd)


def send_hotmail(subject, content, set_obj):
    msg_txt=format_email_dict(content)
    from_email={'login': set_obj.get_email_login(), 'pwd': set_obj.get_email_pwd()}
    to_email='finatos@me.com'

    msg=MIMEText(msg_txt)
    msg['Subject'] = subject
    msg['From'] = from_email['login']
    msg['To'] = to_email
    mail=smtplib.SMTP('smtp.live.com',25)
    mail.ehlo()
    mail.starttls()
    mail.login(from_email['login'], from_email['pwd'])
    mail.sendmail(from_email['login'], to_email, msg.as_string())
    mail.close()


def format_email_dict(content):
    content_tmp=''
    for item in content.keys():
        content_tmp+=str(item)+':'+str(content[item])+'\r\n'
    return content_tmp

