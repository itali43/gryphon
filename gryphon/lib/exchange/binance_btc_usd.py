# -*- coding: utf-8 -*-
"""
Binance BTC / USD
USD is USDC




Error Message Key:
-------------------------

Error message return                    ||  Description 
--------------------------------------------------------------------------------------------------------
"Filter failure: PRICE_FILTER"	            price is too high, too low, and/or not following
                                             the tick size rule for the symbol.
                                             
"Filter failure: PERCENT_PRICE"	            price is X% too high or X% too low 
                                             from the average weighted price over the last Y minutes.
                                             
"Filter failure: LOT_SIZE"              	quantity is too high, too low, 
                                             and/or not following the step size rule for the symbol.
                                             
"Filter failure: MIN_NOTIONAL"             	price * quantity is too low to be a valid order
                                             for the symbol.

"Filter failure: ICEBERG_PARTS"	            ICEBERG order would break into too many parts; 
                                             icebergQty is too small.
                                             
"Filter failure: MARKET_LOT_SIZE"	        MARKET order's quantity is too high, too low, 
                                             and/or not following the step size rule for the symbol.
                                             
"Filter failure: MAX_POSITION"	            The account's position has reached the maximum defined limit.
                                             This is composed of the sum of the balance of the base asset,
                                             and the sum of the quantity of all open BUYorders.
                                             
"Filter failure: MAX_NUM_ORDERS"	        Account has too many open orders on the symbol.

"Filter failure: MAX_ALGO_ORDERS"	        Account has too many open stop loss and/or take profit
                                             orders on the symbol.
                                             
"Filter failure: MAX_NUM_ICEBERG_ORDERS"	Account has too many open iceberg orders on the symbol.

"Filter failure: EXCHANGE_MAX_NUM_ORDERS"	Account has too many open orders on the exchange.

"Filter failure: EXCHANGE_MAX_ALGO_ORDERS"	Account has too many open stop loss and/or take profit 
                                             orders on the exchange.




"""

import base64
from collections import OrderedDict, defaultdict
import hashlib
import hmac
import json
import requests
import time
import urllib
import cdecimal
from cdecimal import Decimal
from operator import itemgetter

from gryphon.lib.exchange import exceptions
from gryphon.lib.exchange import order_types
from gryphon.lib.exchange.exchange_api_wrapper import ExchangeAPIWrapper
from gryphon.lib.logger import get_logger
from gryphon.lib.models.exchange import Balance
from gryphon.lib.money import Money
from gryphon.lib.time_parsing import parse

logger = get_logger(__name__)


class BinanceBTCUSDExchange(ExchangeAPIWrapper):
    def __init__(self, session=None, configuration=None):
        super(BinanceBTCUSDExchange, self).__init__(session)

        self.name = u'BINANCE_BTC_USD'
        self.friendly_name = u'Binance BTC-USD'
        self.base_url = 'https://api.binance.com'
        self.currency = 'USD'
        self.currency_symbol = 'USDC'  # for alt. pair subclasses
        self.volume_currency = 'BTC'
        self.bid_string = 'BUY'
        self.ask_string = 'SELL'
        self.nonce = 1
        self.ticker_symbols = 'BTCUSDC'

        # Configurables with defaults.
        self.market_order_fee = Decimal('0.0004')
        self.limit_order_fee = Decimal('0.0002')
        # https://www.binance.com/en/fee/futureFee

        self.fee = Decimal('0.0002')  # TODO: update for tot volume
        self.fiat_balance_tolerance = Money('0.0001', self.currency)
        self.volume_balance_tolerance = Money('0.00000001', self.volume_currency)
        self.max_tick_speed = 1
        self.min_order_size = Money('0', self.volume_currency)
        self.use_cached_orderbook = False

        self.ping_url = '/wapi/v3/systemStatus.html'
        self.pair_details = '/api/v3/exchangeInfo'

        self.balance_url = '/api/v3/account' 

        self.ticker_url = '/api/v3/ticker/24hr'
        self.orderbook_url = '/api/v3/depth'
        
        self.trades_url = '/userTrades'
        
        self.order_url = '/api/v3/order'
        self.open_orders_url = '/api/v3/openOrders'
        
        self.transactions_url = '/allOrders'

        if configuration:
            self.configure(configuration)

    # Request implementation methods.

    def auth_request(self, req_method, url, request_args):
        """
        This modifies request_args.
        """
        self.load_creds()

        if 'headers' not in request_args:
            request_args['headers'] = {}

        headers = request_args['headers']
        headers.update({'Content-Type': 'application/json'})
        headers.update({"X-MBX-APIKEY": self.api_key})

        # DELETE and POST use the above content-type, GET uses this one.
        if req_method.lower() == 'get':
            headers.update({"Content-Type": "application/x-www-form-urlencoded"})

        if 'params' not in request_args:
            request_args['params'] = {}

        params = request_args['params']
        params.update({
            "recvWindow": 60000,
            "timestamp": str(self.get_current_timestamp() - 1000),
        })

        # Get the raw query string, turn it into a sig, and add it to the params.
        params['signature'] = self._get_signature(self.secret, params)

    def load_creds(self):
        try:
            self.api_key
            self.secret
        except AttributeError:
            self.api_key = self._load_env('BINANCE_BTC_USD_API_KEY')
            self.secret = self._load_env('BINANCE_BTC_USD_API_SECRET')

    def get_current_timestamp(self):
        return int(round(time.time() * 1000))

    def _get_signature(self, secret_key, params):
        query_string = urllib.urlencode(params)

        signature = hmac.new(
            secret_key.encode(),
            msg=query_string.encode(),
            digestmod=hashlib.sha256,
        ).hexdigest()

        return signature

    def resp(self, req):
        response = super(BinanceBTCUSDExchange, self).resp(req)
        return response

    # Exchange Trading Interface implementations.



    
    def get_balance_req(self):
        """
        Get Balance for currencies
        
        Return format:
        {"balances": [{"asset": "BTC", "free": "4723846.89208129", 
        "locked": "0.00000000"}, {...}],
        ...}
        https://binance-docs.github.io/apidocs/spot/en/#account-information-user_data
        """

        return self.req(
            'get',
            self.balance_url,
            no_auth=False,
        )

    def get_balance_resp(self, req):
        """
            Balance grabs the BTC Amount and USD Amount
        """
        resp = self.resp(req)
        balance = Balance()
        
        response = self.resp(req)

        try:
            for bal in response['balances']:
                # vol currency
                if bal['asset'] == self.volume_currency:
                    
                    balance[self.volume_currency] = Money(bal['free'], self.volume_currency)
                
                # currency (using currency_symbol to match to USDC b/c of 3 letter symbols limitation)
                if bal['asset'] == self.currency_symbol:  
                    
                    balance[self.currency] = Money(bal['free'], self.currency)
                
                
        except KeyError:
            raise exceptions.ExchangeAPIErrorException(self, 'malformed response')

        # try:
        #     for account in account_data["assets"]:
        #         if account['asset'] == self.currency_symbol:
        #             max_amt_w = account['maxWithdrawAmount']
        #             balance[self.currency] = Money(max_amt_w, self.currency)
        # except KeyError:
        #     raise exceptions.ExchangeAPIErrorException(self, 'malformed response')

        return balance

    def get_ticker_req(self, verify=True):
        payload = {"symbol": "BTCUSDC"}
        return self.req(
            'get',
            self.ticker_url,
            no_auth=True,
            # verify=verify,
            params=payload,
        )

    def get_ticker_resp(self, req):
        response = self.resp(req)
        print(response)
        return {
            'high': Money(response['highPrice'], 'USD'),
            'low': Money(response['lowPrice'], 'USD'),
            'last': Money(response['lastPrice'], 'USD'),
            'volume': Money(response['volume'], 'BTC')
        }

    def _get_orderbook_from_api_req(self, verify=True):
        payload = {"symbol": "BTCUSDC"}
        return self.req(
            'get',
            self.orderbook_url,
            no_auth=True,
            verify=verify,
            params=payload,
        )

    def place_order_req(self, mode, volume, price=None, order_type=order_types.LIMIT_ORDER):
        """
        Nice to know the Time In Force Options, so why not here:
            (this wrapper defaults to GTC, as do api examples on web)
            GTC - Good Till Cancel
            IOC - Immediate or Cancel
            FOK - Fill or Kill
            GTX - Good Till Crossing (Post Only)

        Why not list all the types, with add. params required too!:

            Type	                              Additional mandatory parameters
            ---------------------------------------------------------------------
            LIMIT	                              timeInForce, quantity, price
            MARKET	                              quantity
            STOP/TAKE_PROFIT                      quantity, price, stopPrice
            STOP_MARKET/TAKE_PROFIT_MARKET	      stopPrice
            TRAILING_STOP_MARKET	              callbackRate

        """

        # symbol, side, type, timestamp, time in force, quantity

        side = self._order_mode_from_const(mode)

        if price.currency != self.currency:
            raise ValueError('price must be in %s' % self.currency)
        if volume.currency != self.volume_currency:
            raise ValueError('volume must be in %s' % self.volume_currency)

        # Truncate the volume instead of rounding it because it's better# to trade too
        # little than too much.
        volume = volume.round_to_decimal_places(8, rounding=cdecimal.ROUND_DOWN)

        quantity = '%.8f' % volume.amount
        price = '%.2f' % price.amount
        time_in_force = "GTC"
        ord_type = 'LIMIT'
        if order_type == order_types.LIMIT_ORDER:
            ord_type = 'LIMIT'
        else:
            # TODO: Test this, add more types as requested
            ord_type = 'MARKET'
            time_in_force = None
            price = None

        params = {
            "type": ord_type,
            "symbol": self.ticker_symbols,
            "side": side,
            "quantity": quantity,
            "price": price,
            "timeInForce": time_in_force,
        }

        return self.req('post', self.order_url, params=params)

    def place_order_resp(self, req):
        """
            {
                u'avgPrice': u'0.00000',
                u'clientOrderId': u'VZleNDFwm62ScMM4hB5FTh',
                u'closePosition': False,
                u'cumQty': u'0',
                u'cumQuote': u'0',
                u'executedQty': u'0',
                u'orderId': 5372915335,
                u'origQty': u'0.030',
                u'origType': u'LIMIT',
                u'positionSide': u'BOTH',
                u'price': u'8000',
                u'reduceOnly': False,
                u'side': u'BUY',
                u'status': u'NEW',
                u'stopPrice': u'0',
                u'symbol': u'BTCUSDT',
                u'timeInForce': u'GTC',
                u'type': u'LIMIT',
                u'updateTime': 1593136966400,
                u'workingType': u'CONTRACT_PRICE'
            }

        """
        resp = self.resp(req)
        print(resp)
        print('++++++')

        try: 
            order_id = '%s' % resp['orderId']
        except KeyError:
            successed = False
        return {'success': True, 'order_id': order_id}

            

    def get_open_orders_req(self):
        params = {
            'symbol': self.ticker_symbols,
        }

        return self.req('get', self.open_orders_url, params=params)

    def get_open_orders_resp(self, req):
        """
        Get Details of an order
        """
        raw_orders = self.resp(req)
    
        orders = []

        for raw_order in raw_orders:
            mode = self._order_mode_to_const(raw_order['side'])
            volume = Money(raw_order['origQty'], self.volume_currency)
            volume_filled = Money(raw_order['executedQty'], self.volume_currency)
            vol_remain_raw = volume.amount - volume_filled.amount
            volume_remaining = '%.8f' % vol_remain_raw

            order = {
                'mode': mode,
                'id': '%s' % raw_order['orderId'],
                'price': Money(raw_order['price'], self.currency),
                'volume': volume,
                'volume_remaining': Money(volume_remaining, self.volume_currency),
                'status': raw_order['status'],
            }
            orders.append(order)

        return orders

    def get_order_details(self, order_id):
        oid = '%s' % order_id
        req = self.get_order_details_req(oid)
        return self.get_order_details_resp(req, oid)

    def get_order_details_req(self, order_id):
        oid_int = int(order_id)
        params = {
            'symbol': self.ticker_symbols,
            'orderId': oid_int,
        }

        return self.req('get', self.order_url, params=params)

    def get_order_details_resp(self, req, order_id):
        """
            Get Order Details
            https://binance-docs.github.io/apidocs/spot/en/#query-order-user_data
        """
        order_details = self.resp(req)
        oid = '%s' % order_details["orderId"]
        time_created = order_details["time"]
        print(order_details)

        side = self._order_mode_to_const(order_details["side"])

        total_volume_currency = order_details["origQty"]
        vol_currency_final = Money(total_volume_currency, self.volume_currency)
        price_calc = Decimal(order_details["origQty"]) * Decimal(order_details["price"])
        total_price_currency = '%.2f' % price_calc
        time_created = round(Decimal(order_details["time"]) / Decimal(1000))

        data = {
            'time_created': time_created,
            'type': side,
            '%s_total' % self.volume_currency.lower(): vol_currency_final,
            'fiat_total': Money(total_price_currency, self.currency),
            'trades': [],
        }
        return data

    def get_multi_order_details(self, order_ids):
        order_dict = {}
        for order in order_ids:
            order_dict.update(self.get_order_details(order))
        return order_dict


    def cancel_order_req(self, order_id):
        params = {
            'symbol': self.ticker_symbols,
            'orderId': int(order_id),
        }

        return self.req('delete', self.order_url, params=params)

    def cancel_order_resp(self, req):
        """
        when called on a ID that doesnt exist:
        {u'msg': u'Unknown order sent.', u'code': -2011}
        Otherwise a bunch of data on the order
        TODO: an error case would be nice here when cancel has been done, etc
        """

        response = self.resp(req)
        successed = False
        try:
            tried = response['status']
            if tried == 'CANCELED' or 'CANCELLED':
                successed = True
        except KeyError:
            successed = False

        return {'success': successed}

    def all_trades(self):
        req = self.all_trades_req()
        return self.all_trades_resp(req)

    def all_trades_req(self):
        params = {
            'symbol': self.ticker_symbols,
        }
        return self.req('get', self.transactions_url, params=params)

    def all_trades_resp(self, req):
        return self.resp(req)

    def get_order_audit_data(self, skip_recent=0, page=1):
        """
        Returns an OrderedDict of order ids mapped to their filled volume (only include
        orders that have some trades).
        Dropped the skip_recent flag because we don't seem to be using it anywhere.
        """
        if skip_recent != 0:
            raise ValueError('skip_recent is deprecated')
        trades_to_audit = []
        orders = OrderedDict()

        # TODO: Implement an "all_Trades" or "get_all_trades" fn you can use here.
        trades = self.all_trades()

        for trade in trades:
            if Decimal(trade['executedQty']) != Decimal('0'):
                our_type = trade['side']
                fiat_raw = Decimal(trade['executedQty']) * Decimal(trade['avgPrice'])
                fiat = Money('%s' % fiat_raw, self.currency)
                fee_raw = self.fee * fiat_raw
                fee = Money('%.8f' % fee_raw, self.currency)
                btc_raw = Decimal(trade['executedQty'])
                btc = Money('%s' % btc_raw, self.volume_currency)

                trade_dict = {
                    'time': trade["time"],
                    'trade_id': str(trade['orderId']),  # none given by Binancef
                    'order_id': str(trade['orderId']),
                    'btc': btc,
                    'fiat': fiat,
                    'fee': fee,
                    'type': our_type,
                }

                trades_to_audit.append(trade_dict)

        # Trades from the same order aren't guaranteed to be next to each other, so we
        # need to group them.
        trades_to_audit.sort(key=lambda t: (t['time']), reverse=True)
        for trade in trades_to_audit:
            order_id = str(trade['order_id'])

            try:
                orders[order_id] += abs(trade['btc'])
            except KeyError:
                orders[order_id] = abs(trade['btc'])

        # Remove the oldest 2 orders, because its trades might be wrapped around a
        # page gap and this would give us an innacurate volume_filled number.
        # We need to remove 2 because there could be an ask and a bid.
        try:
            orders.popitem()
            orders.popitem()
        except KeyError:
            pass

        return orders

    # Random endpoint implementations.

    def get_ping(self):
        requested = self.req('get', self.ping_url, no_auth=True)
        return self.resp(requested)


    def get_pair_details(self):
        requested = self.req('get', self.pair_details, no_auth=True)
        resp = self.resp(requested)
        for i in resp['symbols']:
            if i['symbol'] == self.ticker_symbols:
                return i
            
        