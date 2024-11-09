from typing import Any
import requests
import alpaca_trade_api as tradeapi
import math
from datetime import datetime
import yfinance as yf
import threading

api_key = ''
secrets = ''
base_url = 'https://paper-api.alpaca.markets'
api = tradeapi.REST(api_key, secrets, 'https://api.alpaca.markets')
symbol = "QQQ"
risk_free_rate = 0.054465  # LIBOR

headers = {
    "accept": "application/json",
    "APCA-API-KEY-ID": api_key,
    "APCA-API-SECRET-KEY": secrets
}


def get_valid_expiration_dates(ticker: str):
    stock = yf.Ticker(ticker)
    expiration_dates = stock.options
    return expiration_dates


def normalize_date_format(date_str: str) -> str:
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    return date_obj.strftime('%Y%m%d')


def generate_option_symbols(ticker: str, expiration: str, current_price: float):
    stock = yf.Ticker(ticker)
    options = stock.option_chain(datetime.strptime(expiration, '%Y%m%d').strftime('%Y-%m-%d'))

    lower_bound = current_price * 0.95
    upper_bound = current_price * 1.05

    call_symbols = []
    for call in options.calls.to_dict('records'):
        if lower_bound <= call['strike'] <= upper_bound:
            call_symbols.append(f"{ticker}{expiration[2:]}C{str(int(call['strike'] * 1000)).zfill(8)}")
        elif call['strike'] > upper_bound:
            break

    put_symbols = []
    for put in options.puts.to_dict('records'):
        if lower_bound <= put['strike'] <= upper_bound:
            put_symbols.append(f"{ticker}{expiration[2:]}P{str(int(put['strike'] * 1000)).zfill(8)}")
        elif put['strike'] > upper_bound:
            break

    return call_symbols, put_symbols


class OptionString:
    def __init__(self, option_string: str):
        self.option_string = option_string
        self.symbol = self.parse_symbol()
        self.expiration = self.parse_expiration()
        self.option_type = self.parse_option_type()
        self.strike_price = self.parse_strike_price()

    def parse_symbol(self) -> str:
        # Check if the ticker is 3 or 4 characters long
        if self.option_string[4] in ['C', 'P']:
            return self.option_string[:3]
        else:
            return self.option_string[:4]

    def parse_expiration(self) -> str:
        if len(self.symbol) == 3:
            return "20" + self.option_string[3:9]
        else:
            return "20" + self.option_string[4:10]

    def parse_option_type(self) -> str:
        if len(self.symbol) == 3:
            return self.option_string[9]
        else:
            return self.option_string[10]

    def parse_strike_price(self) -> float:
        if len(self.symbol) == 3:
            return int(self.option_string[10:]) / 1000
        else:
            return int(self.option_string[11:]) / 1000

    def __str__(self) -> str:
        return (f"Option String: {self.option_string}\n"
                f"Symbol: {self.symbol}\n"
                f"Expiration: {self.expiration}\n"
                f"Type: {self.option_type}\n"
                f"Strike Price: {self.strike_price:.2f}")


class OptionSpread:
    def __init__(self, symbol, expiration, strike, risk_free_rate, price, call_symbol, put_symbol):
        self.symbol = symbol
        self.expiration = expiration
        self.strike = strike
        self.risk_free_rate = risk_free_rate
        self.price = price
        self.call_symbol = call_symbol
        self.put_symbol = put_symbol
        self.call = get_option_data(self.call_symbol, headers)
        self.put = get_option_data(self.put_symbol, headers)
        self.call_value = float(self.call['quotes'][self.call_symbol]['ap'])
        self.put_value = float(self.put['quotes'][self.put_symbol]['ap'])
        self.call_put_difference = self.call_value - self.put_value
        self.strike_present_value = self.present_value_of_strike()
        self.strike_diff = self.price - self.strike_present_value

    def present_value_of_strike(self):
        return self.strike * math.exp(-self.risk_free_rate * (float(days_till_expiration(self.expiration) / 365)))

    def calculate_profit(self):
        if self.strike_diff < self.call_put_difference:
            return (self.strike + (self.call_value - self.put_value) - self.price) * 100
        else:
            return (self.price + (self.put_value - self.call_value) - self.strike) * 100

    def print_option_info(self):
        print(f"Call Value: {self.call_value}")
        print(f"Put Value: {self.put_value}")
        print(f"Call, Put Difference: {self.call_put_difference}")
        print(f"Strike: {self.strike}")
        print(f"Price, Strike Difference: {self.strike_diff}")
        print(f"Price is {self.price}")
        print(f"Profit is {self.calculate_profit()}")
        print("----------------------------------")


def get_option_data(symbol, headers):
    url = f"https://data.alpaca.markets/v1beta1/options/quotes/latest?symbols={symbol}&feed=indicative"
    response = requests.get(url, headers=headers)
    return response.json()


def days_till_expiration(expiration_date):
    expiration_date = datetime.strptime(expiration_date, '%Y%m%d')
    current_date = datetime.now()
    delta = expiration_date - current_date
    return delta.days + 1


def present_value_of_strike(strike_price, risk_free_rate, time_to_expiration):
    return strike_price * math.exp(-risk_free_rate * (float(time_to_expiration / 365)))


def process_option_spread(call, put_symbol, price, spread_list):
    call_data = get_option_data(call.option_string, headers)
    put_data = get_option_data(put_symbol, headers)
    call_value = float(call_data['quotes'][call.option_string]['ap'])
    put_value = float(put_data['quotes'][put_symbol]['ap'])
    strike = call.strike_price
    strike_present_value = present_value_of_strike(strike, risk_free_rate, days_till_expiration(expiration))
    strike_diff = price - strike_present_value
    spread_list.append(
        OptionSpread(symbol, expiration, strike, risk_free_rate, price, call.option_string, put_symbol))


valid_expirations = get_valid_expiration_dates(symbol)
expiration = normalize_date_format(valid_expirations[2])
print(expiration)

last_trade = api.get_latest_trade(symbol)
price = last_trade.price

call_symbols, put_symbols = generate_option_symbols(symbol, expiration, price)

call_options = [OptionString(call) for call in call_symbols]
put_options = [OptionString(put) for put in put_symbols]

spread_list = []
threads = []

for call in call_options:
    put_symbol = call.option_string.replace("C", "P")
    if put_symbol in put_symbols:
        thread = threading.Thread(target=process_option_spread, args=(call, put_symbol, price, spread_list))
        thread.start()
        threads.append(thread)

for thread in threads:
    thread.join()

spread_list.sort(key=lambda x: x.calculate_profit())
for spread in spread_list:
    spread.print_option_info()
