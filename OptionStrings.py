import yfinance as yf
from datetime import datetime

def un_normalize_date_format(date_str: str) -> str:
    # Convert to datetime object
    date_obj = datetime.strptime(date_str, '%y%m%d')
    # Convert back to string in desired format
    return (date_obj.strftime('%Y-%m-%d'))


def generate_option_symbols(ticker: str, expiration: str):
    # Create a Yahoo Finance ticker object
    stock = yf.Ticker(ticker)
    current_price = stock.history(period='1d')['Close'][0]

    options = stock.option_chain(un_normalize_date_format(expiration))

    # Calculate the 15% range
    lower_bound = current_price * 0.95
    upper_bound = current_price * 1.05
    print(lower_bound, upper_bound)
    # Extract call and put options within the 15% range
    calls = [call for call in options.calls.to_dict('records') if lower_bound <= int(call['strike']) <= upper_bound]
    puts = [put for put in options.puts.to_dict('records') if lower_bound <= int(put['strike']) <= upper_bound]

    # Format the call and put option symbols and create separate lists
    call_symbols = [
        f"{ticker}{expiration}C{str(int(call['strike'] * 1000)).zfill(8)}"
        for call in calls
    ]

    put_symbols = [
        f"{ticker}{expiration}P{str(int(put['strike'] * 1000)).zfill(8)}"
        for put in puts
    ]

    return call_symbols, put_symbols


def get_valid_expiration_dates(ticker):
    # Create a Yahoo Finance ticker object
    stock = yf.Ticker(ticker)

    # Get the available expiration dates
    expiration_dates = stock.options

    return expiration_dates


