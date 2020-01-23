import sys
from lightstreamer_client import LightstreamerClient
from lightstreamer_client import LightstreamerSubscription
import pip

# A simple function acting as a Subscription listener
def on_item_update(item_update):
    print(item_update)
    print("{MarketId}, {TickDate}, {Bid}, {Offer}, {Price}".format(**item_update["values"]))

    # Adding the "on_item_update" function to Subscription

def wait_for_input():
    input("{0:-^80}\n".format("HIT CR TO UNSUBSCRIBE AND DISCONNECT FROM LIGHTSTREAMER"))

def main(args):



    lightstreamer_client = LightstreamerClient("DA948755", "40303ba1-a94b-48c2-a543-f86769d870b1", "https://push.cityindex.com", "STREAMINGALL")

    try:
        lightstreamer_client.connect()
    except Exception as e:
        print("Unable to connect to Lightstreamer Server", e)

    # Making a new Subscription to "PRICES" Data Adapter
    subscription = LightstreamerSubscription(adapter="PRICES", mode = "MERGE", items=["PRICE.401484347"], fields = ["MarketId", "TickDate", "Bid", "Offer", "Price"])

    subscription.addlistener(on_item_update)

    sub_key = lightstreamer_client.subscribe(subscription)

    while True:

        None



if __name__=='__main__':
    sys.exit(main(sys.argv))








