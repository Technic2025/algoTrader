import alpaca_trade_api as tradeapi
import yfinance as yf
import yahoo_fin.stock_info as si
from datetime import datetime as dt
import pytz
import numpy as np
import datetime
import time
import pandas as pd

key = ""
sec = ""
url = "https://paper-api.alpaca.markets"

api = tradeapi.REST(key, sec, url, api_version='v2')

account = api.get_account()

def check_open():
    return api.get_clock().is_open

def get_current_price(ticker):
    return si.get_live_price(ticker)

def get_moving_averages(ticker):
    #Returns [lower]-day and [upper]-day moving averages
    lower = 8
    upper = 20

    today = datetime.datetime.today().isoformat()

    tickerdata=yf.Ticker(ticker)
    tickerDF = tickerdata.history(period='1D', start="2021-2-1", end=today[:10])
    
    one_less_long = np.sum(tickerDF["Close"].iloc[-(upper - 1):])
    one_less_short = np.sum(tickerDF["Close"].iloc[-(lower - 1):])

    current = get_current_price(ticker)

    longer_range = (one_less_long + current) / upper
    shorter_range = (one_less_long + current) / lower

    return longer_range, shorter_range

def findTrend(ticker):
    trend = -1
    averages = get_moving_averages(ticker)
    if averages[1] > averages[0]:
        trend = 1
    
    return trend

def sell(ticker, num):
    order = api.submit_order(symbol=ticker, qty=str(num), side="sell", type="market", time_in_force="day")
    print("Sold " + str(int(num)) + " shares of " + ticker + " [" + get_current_time() + "]")
    time.sleep(5)

def buy(ticker, num):
    order = api.submit_order(symbol=ticker, qty=str(num), side="buy", type="market", time_in_force="day")
    print("Bought " + str(int(num)) + " shares of " + ticker + " [" + get_current_time() + "]")
    time.sleep(5)

def get_current_time():
    return dt.now(pytz.timezone("America/New_York")).strftime("%H:%M:%S")

print()
print("Starting... [" + get_current_time() + "]")

payload = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
first_table = payload[0]
second_table = payload[1]

df = first_table

df.head()

symbols = df['Symbol'].values.tolist()

tickers = symbols[:500] #Looks like this: ["FB", "TSLA", "GME", "GOOG", "AAPL", "AMZN", ...]

tickers.remove("BRK.B") #invalid tickers
tickers.remove("BF.B")
tickers.remove("WRK")

stocks = []
positions = api.list_positions()

for position in positions:
    stocks.append([position.symbol, findTrend(position.symbol), int(position.qty)])


for ticker in tickers:
    owned = False
    for stock in stocks:
        if stock[0] == ticker:
            owned = True
    if not owned:
        stocks.append([ticker, findTrend(ticker), 0, 999999])

iteration = 0
while 1:
    if check_open():
        print("Gathering stock information... [" + str(iteration) + "] [" + get_current_time() + "]")
        for stock in stocks:
            account = api.get_account()
            prevTrend = stock[1]
            newTrend = findTrend(stock[0])
            #sells when short-term average dips below long-term average or when there is a 1.5% or more increase from purchase price
            if prevTrend > newTrend or get_current_price(stock[0]) * 1.015 >= stock[3]: 
                if stock[2] > 0:
                    sell(stock[0], stock[2])
                    stock[2] = 0
            elif prevTrend < newTrend:
                available_funds = float(account.buying_power)
                price =  get_current_price(stock[0])
                #buys when short-term average goes above long-term average
                if  0.2 * available_funds >= price:
                    to_buy = .2 * available_funds // price
                    buy(stock[0], to_buy)
                    stock[3] = get_current_price(stock[0])
                    stock[2] += to_buy
            stock[1] = newTrend
        iteration += 1
    else:
        print("Market closed, retrying in 5 minutes [" + get_current_time() + "]")
        time.sleep(300)
