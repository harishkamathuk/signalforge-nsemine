from nsemine.bin import scraper, header
from nsemine.utilities import urls, utils
from datetime import UTC, datetime
from zoneinfo import ZoneInfo
import pandas as pd
import traceback


_NSE_TIMEZONE = ZoneInfo("Asia/Kolkata")


def _intraday_chart_epoch(value: datetime) -> int:
    """Encode an NSE local wall time independent of the machine's timezone.

    The chart endpoint has historically been called with an IST wall-clock value
    represented as Unix-shaped seconds (09:15 IST -> 09:15 UTC-shaped seconds).
    This helper preserves that existing wire convention while removing the
    dependency on naive datetime.timestamp() and the host process timezone.
    Provider response timestamps remain subject to SF-081 verification.
    """
    if not isinstance(value, datetime):
        raise TypeError("Historical bounds must be datetime instances")
    if value.tzinfo is None or value.utcoffset() is None:
        local = value  # Existing naive API inputs mean NSE local wall time.
    else:
        local = value.astimezone(_NSE_TIMEZONE)
    return int(local.replace(tzinfo=UTC).timestamp())




def search_stock_instruments(
    stock_symbol: str,
    segment: str | None = None,
    scrip_type: str | None = None,
) -> list[dict]:
    """Return provider instrument-search candidates without normalizing identity fields.

    This evidence-oriented API intentionally preserves the provider's original
    candidate dictionaries so callers can apply their own fail-closed identity
    policy. It does not select a candidate.
    """
    if not isinstance(stock_symbol, str) or not stock_symbol.strip():
        raise ValueError("stock_symbol must be a non-empty string")

    symbol = stock_symbol.upper()
    segment_set = {"EQ", "FO", "IDX"}
    if segment is not None and segment not in segment_set:
        raise ValueError("segment must be one of EQ, FO, IDX")

    params = {
        "segment": segment or "",
        "symbol": symbol,
    }
    resp = scraper.get_request(url=urls.search_token_url, params=params)
    payload = resp.json()
    raw_candidates = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(raw_candidates, list):
        raise ValueError("provider instrument search returned no candidate list")

    if any(not isinstance(candidate, dict) for candidate in raw_candidates):
        raise ValueError("provider instrument search returned a malformed candidate entry")
    candidates = [dict(candidate) for candidate in raw_candidates]
    if scrip_type is not None:
        if scrip_type not in {"Equity", "Index", "Futures", "Options"}:
            raise ValueError("unsupported scrip_type")
        candidates = [candidate for candidate in candidates if candidate.get("type") == scrip_type]
    return candidates


def get_stock_historical_data_by_instrument(
    symbol: str,
    token: str,
    symbol_type: str,
    start_datetime: datetime,
    end_datetime: datetime = datetime.now(),
    interval: int | str = "D",
    raw: bool = False,
) -> pd.DataFrame | dict | None:
    """Fetch history using an explicitly supplied provider instrument identity.

    Unlike get_stock_historical_data(), this function performs no symbol/token
    lookup. The supplied token is passed directly to the historical chart
    request, allowing an external caller to validate identity once and prove
    which token was used for acquisition.
    """
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("symbol must be a non-empty string")
    if not isinstance(token, str) or not token.strip():
        raise ValueError("token must be a non-empty string")
    if not isinstance(symbol_type, str) or not symbol_type.strip():
        raise ValueError("symbol_type must be a non-empty string")

    return __fetch_historical_data(
        symbol=symbol,
        token=token,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        interval=interval,
        symbol_type=symbol_type,
        raw=raw,
    )


def get_stock_historical_data(stock_symbol: str, 
                            start_datetime: datetime, 
                            end_datetime: datetime = datetime.now(), 
                            interval: int | str = 'D', 
                            raw: bool = False) -> pd.DataFrame | dict | None:
    """
    Fetches historical stock data for a given symbol within a specified datetime range for the given interval.
    The interval can be either in minutes or 'D' for Daily, 'W' for Weekly and 'M' for monthly interval data.
    
    
    Args:
        symbol (str): The stock symbol (e.g., "TCS" etc).
        start_datetime (datetime.datetime): The start datetime for the historical data.
        end_datetime (datetime.datetime, optional): The end datetime for the historical data. Defaults to the current datetime.
        interval (int or str, optional) : The time interval of the historical data. Valid values are 1, 5, 10, 15, 30, 60, 'D', 'W', and 'M'. Defaults to 'D' > Daily.
        raw (bool, optional): If True, returns the raw data without processing. If False, returns processed data. Defaults to False.
    
    Returns:
        data ([pd.DataFrame | dict | None]) : A Pandas DataFrame containing the historical stock data. If you pass raw=True,
        then you will get the data in dictionary format. Returns None If any error occurs during data fetching or processing.
    
    Example:
        - To get the daily interval data.
        >>> df = get_stock_historical_data('TCS', datetime(2025, 1, 1), datetime.now(), interval='D')
    
        - To get 5-minute interval data.
        >>> df = get_stock_historical_data('INFY', datetime(2025, 1, 1), datetime.now(), interval='5')
    """
    try:
        search_result = __get_script_token(symbol=stock_symbol)

        if not search_result:
            raise ValueError("An error occurred. Token not found.")
        
        # unpacking the tuple
        symbol, token, symbol_type = search_result
        
        return __fetch_historical_data(symbol=symbol,
                                    token=token,
                                    start_datetime=start_datetime,
                                    end_datetime=end_datetime,
                                    interval=interval,
                                    symbol_type=symbol_type,
                                    raw=raw)
        
    except Exception as e:
        print(f'ERROR! - {e}\n')
        traceback.print_exc()
        return None



def get_index_historical_data(index: str, 
                        start_datetime: datetime, 
                        end_datetime: datetime = datetime.now(), 
                        interval: int | str = 'D', 
                        raw: bool = False) -> pd.DataFrame | dict | None:
    """
    Fetches historical data for the given index within a specified datetime range for the given interval.
    The interval can be either in minutes or 'D' for Daily, 'W' for Weekly and 'M' for monthly interval data.
    

    Args:
        index (str): The index name (e.g., "NIFTY 50, NIFTY BANK" etc).
        start_datetime (datetime.datetime): The start datetime for the historical data.
        end_datetime (datetime.datetime, optional): The end datetime for the historical data. Defaults to the current datetime.
        interval (int or str, optional) : The time interval of the historical data. Valid values are 1, 5, 10, 15, 30, 60, 'D', 'W', and 'M'. Defaults to 'D' > Daily.
        raw (bool, optional): If True, returns the raw data without processing. If False, returns processed data. Defaults to False.

    Returns:
        data (Union[pd.DataFrame, dict, None]) : A Pandas DataFrame containing the historical data. If you pass raw=True,
        then you will get the data in dictionary format. Returns None If any error occurs during data fetching or processing.


    Example:
        - To get the daily interval data.
        >>> df = get_index_historical_data('NIFTY 50', datetime(2025, 1, 1), datetime.now(), interval='D')

        - To get 5-minute interval data.
        >>> df = get_index_historical_data('NIFTY BANK', datetime(2025, 1, 1), datetime.now(), interval=5)
    """
    try:
        search_result = __get_script_token(symbol=index)
        if not search_result:
            raise ValueError("An error occurred. Token not found.")
        
        # unpacking the tuple
        symbol, token, symbol_type = search_result
        
        return __fetch_historical_data(symbol=symbol,
                                    token=token,
                                    start_datetime=start_datetime,
                                    end_datetime=end_datetime,
                                    interval=interval,
                                    symbol_type=symbol_type,
                                    raw=raw)
        
    except Exception as e:
        print(f'ERROR! - {e}\n')
        traceback.print_exc()
        return None



# ---------------------------------------------#
#               Private Functions              #
# ---------------------------------------------#

def __fetch_historical_data(symbol: str, 
                           token: str,
                           start_datetime: datetime, 
                           end_datetime: datetime, 
                           interval: int | str = 'D',
                           symbol_type: str = 'Index',
                           raw: bool = False,
                           ):
    try:
        chart_type = 'I'
        time_interval = 1
        
        if interval in ('D', 'W', 'M'):
            start_datetime = int(start_datetime.timestamp()) 
            end_datetime = int(end_datetime.timestamp())
            chart_type = interval
        else:
            start_datetime = _intraday_chart_epoch(start_datetime)
            end_datetime = _intraday_chart_epoch(end_datetime)
            time_interval =  int(interval)

        # preparing the payload
        payload = {
            'chartType': chart_type, 
            'fromDate': start_datetime, 
            'symbol': symbol, 
            'symbolType': symbol_type,
            'timeInterval': time_interval,
            'toDate': end_datetime,
            'token': token
        }

        resp = scraper.get_request(url=urls.nse_chart_url, params=payload, headers=header.default_headers)
       
        try:
            raw_data = resp.json()
        except Exception:
            return None

        if raw:
            return raw_data

        if not isinstance(raw_data, dict) or not raw_data.get('data'):
            print(f'No Data Returned for the given symbol: {symbol}')
            return None

        try:
            del raw_data['status']
        except KeyError:
            pass

        df = pd.DataFrame(raw_data['data'])
        df.columns.name = symbol
        df = utils.process_historical_chart_response(df=df, interval=interval, start_datetime=start_datetime, end_datetime=end_datetime)
        return df.drop_duplicates(subset=['datetime']).reset_index(drop=True)

    except Exception as e:
        print(f'FETCH ERROR! - {e}\n')
        return None



def __get_script_token(symbol: str, 
                       segment: str | None = None, 
                       scrip_type: str | None = None) -> tuple | pd.DataFrame |  None:
    try:
        symbol = symbol.upper()
        segment_set = {'EQ', 'FO', 'IDX'}
        params = {
            'segment': segment if segment in segment_set else '',
            'symbol': symbol
        }

        resp = scraper.get_request(url=urls.search_token_url, params=params)
        data = resp.json()
        df = pd.DataFrame(data['data'])
        
        if scrip_type:
            if scrip_type in {'Equity', 'Index', 'Futures', 'Options'}:
                df = df[df['type'] == scrip_type]
                
        df['symbol'] = df['symbol'].str.rsplit('-', n=1).str[0]
        x = df[df['symbol'] == symbol]
        if not len(x):
            x = df[df['symbol'].str.startswith(symbol)]
        if not len(x):
            x = df[df['description'].str.contains(symbol)]
        
        symbol = x.iloc[0]['symbol']   
        token = x.iloc[0]['scripcode']
        type = x.iloc[0]['type']
        return symbol, token, type
    
    except Exception:
        print(f'Could not find the token for the given symbol: {symbol}')
        return None
    