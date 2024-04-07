from locale import setlocale
from pprint import pprint
import ccxt
import time
from datetime import datetime
import pandas as pd
import telegram
import talib as ta


okx_access = ""
okx_secret = ""

tel_token = ""
tel_id = ""
tel_bot = telegram.Bot(token=tel_token)


def GetEMA(ohlcv, period, st):
    open = ohlcv["open"]
    ema = open.ewm(span=period, adjust=False).mean()
    return float(ema[st])


def GetOhlcv(binance, Ticker, period):
    btc_ohlcv = binance.fetch_ohlcv(Ticker, period, limit=1000)
    df = pd.DataFrame(btc_ohlcv, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
    df.set_index('datetime', inplace=True)
    return df


def GetAmount(usd, coin_price, rate):

    target = usd * rate

    amount = round((target / (coin_price * 0.1)) - 0.05, 1)

    if amount < 0.01:
        amount = 0.01

    return amount


def GetCoinNowPrice(exchange, Ticker):
    coin_info = exchange.fetch_ticker(Ticker)
    coin_price = coin_info['last']

    return coin_price


okx = ccxt.okx(config={
    'apiKey': okx_access,
    'secret': okx_secret,
    'password': 'Fldrh!i03',
    'enableRateLimit': True,
    'options': {
        'defaultType': 'swap',
        'adjustForTimeDifference': True,
        'recvWindow': 10000,
    }
})

Target_Coin_Ticker = "ETH-USDT-SWAP"
Target_Coin_Ticker_Binance = "ETH/USDT"


while True:
    try:
        coin_price = GetCoinNowPrice(okx, Target_Coin_Ticker)
        
        balance = okx.fetch_balance()

        position = okx.fetch_position(Target_Coin_Ticker)
        
        amount = 0
        entryPrice = 0
        leverage = 5

        if position != None:
            amount = position['info']['pos']
            buy_amount = amount
            if position['info']['posSide'] == "short":
                amount = int(amount) * -1
                
            entryPrice = float(position['info']['avgPx'])
            leverage = float(position['info']['lever'])

        amount = int(amount)
        abs_amount = abs(amount)

        df = GetOhlcv(okx, Target_Coin_Ticker, '5m')

        rsi = ta.RSI(df['close'], timeperiod=14)

        rsi_up = 70
        rsi_down = 30

        if amount == 0:
            if (rsi[-3] > rsi_up) and (rsi[-4] < rsi[-3]) and (rsi[-3] > rsi[-2]):

                coin_price = GetCoinNowPrice(okx, Target_Coin_Ticker)

                buy_amount = int(GetAmount(float(balance['USDT']['total']), coin_price, 0.98) * leverage)

                okx.create_order(symbol=Target_Coin_Ticker, type='market', side='buy', amount=buy_amount, params={
                    "tdMode": "isolated",
                    "posSide": "long"
                })
                
                firstProfit = int(buy_amount)
                firstPrice = round(coin_price * 1.02, 1)
                okx.create_order(symbol=Target_Coin_Ticker, type='limit', side='sell', amount=firstProfit, price=firstPrice, params={
                    "tdMode": "isolated",
                    "posSide": "long"
                })
        
            if (rsi[-3] < rsi_down) and (rsi[-4] > rsi[-3]) and (rsi[-3] < rsi[-2]):
                coin_price = GetCoinNowPrice(okx, Target_Coin_Ticker)

                buy_amount = int(GetAmount(float(balance['USDT']['total']), coin_price, 0.98) * leverage)

                okx.create_order(symbol=Target_Coin_Ticker, type='market', side='sell', amount=buy_amount, params={
                    "tdMode": "isolated",
                    "posSide": "short"
                })
                
                firstProfit = int(buy_amount)
                firstPrice = round(coin_price * 0.98, 1)
                okx.create_order(symbol=Target_Coin_Ticker, type='limit', side='buy', amount=firstProfit, price=firstPrice, params={
                    "tdMode": "isolated",
                    "posSide": "short"
                })
        
        else:
            revenue_rate = (coin_price - entryPrice) / entryPrice * 100.0
            if amount < 0:
                revenue_rate = revenue_rate * -1.0
            
            danger_rate = -1.3

            if amount > 0:
                if (revenue_rate <= danger_rate):
                    openOrders = okx.fetch_open_orders()
                    
                    for i in openOrders:
                        okx.cancel_order(i['id'], Target_Coin_Ticker)

                    okx.create_order(symbol=Target_Coin_Ticker, type='market', side='sell', amount=amount, params={
                        "tdMode": "isolated",
                        "posSide": "long"
                    })

            if amount < 0:
                    if (revenue_rate <= danger_rate):
                        openOrders = okx.fetch_open_orders()
                        
                        for i in openOrders:
                            okx.cancel_order(i['id'], Target_Coin_Ticker)

                        okx.create_order(symbol=Target_Coin_Ticker, type='market', side='buy', amount=amount, params={
                            "tdMode": "isolated",
                            "posSide": "short"
                        })

        time.sleep(0.3)

    except Exception as e:
        print(e)
        tel_bot.sendMessage(chat_id=tel_id, text="──────────────────"
            + "\n오류: " + str(e))
        time.sleep(0.3)