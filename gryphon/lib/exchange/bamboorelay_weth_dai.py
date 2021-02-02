# -*- coding: utf-8 -*-
"""
Bamboo Relay WETH / DAI
ETH is WETH
ETH is used for 3 letter symbol convenience

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
from delorean import Delorean, epoch
from operator import itemgetter

from gryphon.lib.exchange.consts import Consts
from gryphon.lib.exchange import exceptions
from gryphon.lib.exchange.exchange_order import Order
from gryphon.lib.exchange import order_types
from gryphon.lib.exchange.exchange_api_wrapper import ExchangeAPIWrapper
from gryphon.lib.logger import get_logger
from gryphon.lib.models.exchange import Balance
from gryphon.lib.money import Money
from gryphon.lib.time_parsing import parse


from Crypto.Hash import keccak


logger = get_logger(__name__)


class BambooETHDAIExchange(ExchangeAPIWrapper):
    def __init__(self, session=None, configuration=None):
        super(BambooETHDAIExchange, self).__init__(session)

        self.name = u'BAMBOO_ETH_DAI'
        self.friendly_name = u'Bamboo ETH-DAI'
        
        # Bamboo Base URLs
        self.bamboo_main_base_url = 'https://rest.bamboorelay.com/main/0x' # 'https://rest.bamboorelay.com/main/0x/'
        self.bamboo_test_base_url = 'https://rest.bamboorelay.com/ropsten/0x'
        
        # Infura Base URLs
        self.infura_main_base_url = 'https://mainnet.infura.io/v3/aa86ab760dbc4b08994603ff64545382'
        self.infura_test_base_url = 'https://ropsten.infura.io/v3/aa86ab760dbc4b08994603ff64545382'

        self.currency = 'DAI'
        self.currency_symbol = 'DAI'  # TODO: Recheck/refactor
        self.volume_currency = 'ETH'
        self.bid_string = 'BID'
        self.ask_string = 'ASK'
        self.nonce = 1
        self.ticker_symbols = 'DAI-WETH'

        # Configurables with defaults.
        self.market_order_fee = Decimal('0.0004')
        self.limit_order_fee = Decimal('0.0002')
        # TODO: REFACTOR, these fees aren't correct..

        self.fee = Decimal('0.0002')  # TODO: update for tot volume
        self.fiat_balance_tolerance = Money('0.0001', self.currency)
        self.volume_balance_tolerance = Money('0.00000001', self.volume_currency)
        self.max_tick_speed = 1
        self.min_order_size = Money('0', self.volume_currency)
        self.use_cached_orderbook = False

        # Bamboo endings
        self.ping_url = '/orders/fees'
        self.market_depth_url = '/depth'
        self.ticker_url = '/markets/%s/ticker' % self.ticker_symbols
        self.orderbook_url = '/markets/%s/book' % self.ticker_symbols


        self.position_url = '/positionRisk'
        self.trades_url = '/userTrades'
        self.order_url = '/order'
        self.open_orders_url = '/openOrders'
        self.transactions_url = '/allOrders'

        if configuration:
            self.configure(configuration)

    # Request implementation methods.

    def auth_request(self, req_method, url, request_args):
        """
        Authorize for Bamboo, in progress/dep
        """
        self.load_creds()

        
        # req_method = req_method.upper()
        # timestamp = unicode(int(round(time.time())))

        # # This has already been dumped to json by req().
        # body = request_args['data']
        
        # if self.network == 'mainnet':
        #     self.auth_url = self.bamboo_main_base_url
        # else:
        #     self.auth_url = self.bamboo_test_base_url 
        # print(self.auth_url)
        # endpoint = url.replace(self.auth_url, '')
        # print(endpoint)
        # data = timestamp + req_method + endpoint + body
        # key = base64.b64decode(self.secret)
        # sig = base64.b64encode(hmac.new(key, data, hashlib.sha256).digest())

        # try:
        #     headers = request_args['headers']
        # except KeyError:
        #     headers = request_args['headers'] = {}

        # headers.update({
        #     'Content-Type': 'application/json'
        # })


    def load_creds(self):
        # Get which network first main / test 
        try: 
            self.network
            print("network made it")
            
        except AttributeError:
            self.network = self._load_env('NETWORK')
            print("network REFRESHED!")
        
        print("you have entered the %s network.  Welcome." % self.network)
        try:
            self.infura_project_key
            self.secret
            self.api_key
            
            self.vol_currency_contract_addr
            self.currency_contract_addr
            
        except AttributeError:
            
            if self.network == 'mainnet':
                print("it's main get smart contract from main")
                self.currency_contract_addr = self._load_env('BAMBOORELAY_WETH_DAI_CURRENCY_ADDR')
                self.vol_currency_contract_addr = self._load_env('BAMBOORELAY_WETH_DAI_VOL_CURRENCY_ADDR')
            else: 
                print("it's ropsten get smart contract from ropsten")
                self.currency_contract_addr = self._load_env('BAMBOORELAY_WETH_DAI_CURRENCY_ADDR_TEST')
                self.vol_currency_contract_addr = self._load_env('BAMBOORELAY_WETH_DAI_VOL_CURRENCY_ADDR_TEST')
            
            
            self.infura_project_key = self._load_env('INFURA_PROJECT_ID')
            self.secret = self._load_env('BAMBOO_PR')
            self.api_key = self._load_env('BAMBOO_P')

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
        response = super(BambooETHDAIExchange, self).resp(req)
        return response

    # Exchange Trading Interface implementations.



    
    def get_balance_req(self):
        """
        Get Balances for from Wallet via Infura
        Calling ERC20s using addresses and eth_call
        Make sure both mainnet and test are supplied in env
        """
        self.balance_url = ':\'('
        self.load_creds()
        if self.network == 'mainnet':
            self.balance_url = self.infura_main_base_url
        else:
            self.balance_url = self.infura_test_base_url 



        body = {"jsonrpc":"2.0","method":"eth_getBalance","params": "['0x20598860Da775F63ae75E1CD2cE0D462B8CEe4C7', 'latest']","id":1}

               
        headers = {'Content-Type': 'application/json'}
        params = []
        params = {
            'ADDRESS': self.api_key
        }
        params['BLOCK PARAMETER'] = 'latest'

        # NOTE: pip install pycryptodome (added for keccak)
        # NOTE: Error add (handled some by exceptions in resp):        
        # "error": { "message": "execution reverted: Dai/insufficient-balance",....

        # convert using keccak then take first four bytes as a signature (func Selector)
        # Left the process in for replication if necessary for other calls
        
        # k = keccak.new(digest_bits=256)
        # k.update('balanceOf(address)')
        # print k.hexdigest()
        # value = k.hexdigest()
        # print(value)
        # funcSelector = self.sub_bytes(value, 60, 64) # first 4 bytes
        # print("0x70a08231 == This is funcSelector")
        
        
        # formulate data to send in eth_call for the Volume Currency (WETH)
        walletAddress = self.api_key[2:]
        sendit = "0x70a08231" + "000000000000000000000000" + walletAddress
        # print(sendit)
        
        data = '{"jsonrpc":"2.0","method":"eth_call","params": [{"to": "%s","data": "%s"}, "latest"],"id":1}' % (self.vol_currency_contract_addr, sendit)


        # formulate data to send in eth_call for the Currency (DAI)
        walletAddress = self.api_key[2:] # remove 0x on public eth addr
        sendit_cur = "0x70a08231" + "000000000000000000000000" + walletAddress
        # print(sendit_cur)
        
        data_cur = '{"jsonrpc":"2.0","method":"eth_call","params": [{"to": "%s","data": "%s"}, "latest"],"id":1}' % (self.currency_contract_addr, sendit_cur)
        

        
        # payload retrieves normal ETH balance
        # data = '{"jsonrpc":"2.0","method":"eth_getBalance","params": ["%s", "latest"],"id":1}' % self.api_key

        return [self.req( # volume currency (WETH)
            'post',
            self.balance_url,
            headers=headers,
            data=data,
            params=params,
            # no_auth=False,
        ), self.req( # currency (DAI)
            'post',
            self.balance_url,
            headers=headers,
            data=data_cur,
            params=params,
        )]

    def get_balance_resp(self, req):
        """
            Balance grabs the WETH (treated as ETH in gryphon) Amount and DAI Amount
        """
        resp_vol = self.resp(req[0])
        resp_cur = self.resp(req[1])
        
        bal_vol = 0.0
        bal_cur = 0.0
        
        try:
            # Vol Currency Balance
            naked_vol = resp_vol["result"][2:].lstrip("0")
            # divide by 10^18 b/c eth and dai are both 18 decimal places
            bal_vol = float.fromhex(naked_vol)/(10**18) # WETH
            
        except:
            print("error in balance vol currency request: %s" % resp_vol['error'])
            raise exceptions.ExchangeAPIErrorException(self, 'malformed response')

        try:
            # Currency Balance 
            naked_cur = resp_cur["result"][2:].lstrip("0")            
            # divide by 10^18 b/c eth and dai are both 18 decimal places
            bal_cur = float.fromhex(naked_cur)/(10**18) # DAI            
        except:
            print("error in balance currency request: %s" % resp_cur['error'])
            raise exceptions.ExchangeAPIErrorException(self, 'malformed response')
        
        # create balance 
        balance = Balance()
        
        # response = self.resp(req)

        try:
            # vol currency
            
                
            balance[self.volume_currency] = Money(str(bal_vol), self.volume_currency)
            
            # currency (using currency_symbol to match to USDC b/c of 3 letter symbols limitation)
            balance[self.currency] = Money(str(bal_cur), self.currency)
            
        except:
            print("There has been an error in extracting balances.")
        
        return balance
        # return balance

    def get_ticker_req(self, verify=True):
        self.base = ''
        self.load_creds()
        if self.network == 'mainnet':
            self.base = self.bamboo_main_base_url
        else:
            self.base = self.bamboo_test_base_url 

        url = self.base + self.ticker_url
        print(url)
        
        return self.req(
            'get',
            url,
            # no_auth=False,
            # verify=verify,
            # params=payload,
        )

    def get_ticker_resp(self, req):
        response = self.resp(req)
        print(response)
        
        # {u'ticker': {u'bestBid': u'0.0010000000000000000000',
        #              u'price': u'0.0010000000000000000000',
        #               u'bestAsk': u'0.0000000000000000000000', 
        #               u'spreadPercentage': u'0.00000000', 
        #               u'size': u'0.050000000000000000'
        #               }, u'id': u'DAI-WETH'}
        return {
            'high': Money(response['ticker']['bestAsk'], 'ETH'),
            'low': Money(response['ticker']['bestBid'], 'ETH'),
            'last': Money(response['ticker']['price'], 'ETH'),
            'volume': Money('0', 'ETH'),
        }

    def _get_orderbook_from_api_req(self, verify=True):
        # /markets/[marketId]/book
        self.load_creds()
        
        self.base = ''
        
        if self.network == 'mainnet':
            self.base = self.bamboo_main_base_url
        else:
            self.base = self.bamboo_test_base_url 

        url = self.base + self.orderbook_url
        
        return self.req(
            'get',
            url,
            # no_auth=False,
            # verify=verify,
            # params=payload,
        )
        
    def _get_orderbook_from_api_resp(self, req):
        response = self.resp(req)

        asks = []
        bids = []
        
        for i in response["asks"]:

            ask_price = i['price']
            ask_volume = i['remainingBaseTokenAmount']   
             
            asks.append(Order(ask_price, ask_volume, self, Order.ASK))
            
        for i in response["bids"]:

            bid_price = i['price']
            bid_volume = i['remainingBaseTokenAmount']    
            
            bids.append(Order(bid_price, bid_volume, self, Order.BID))
        
        return {'bids': bids, 'asks': asks}
    
    
    def get_orderbook_resp(self, req, volume_limit=None):
        if req == ExchangeAPIWrapper.CACHED_ORDERBOOK:
            return self._get_orderbook_from_cache(volume_limit)
        else:
            parsed_orderbook = self._get_orderbook_from_api_resp(req)

            # parsed_orderbook = self.parse_orderbook(raw_orderbook, volume_limit)
            parsed_orderbook['time_parsed'] = Delorean().epoch

            return parsed_orderbook
    
    
    # def get_orderbook_resp(self, req, volume_limit=None):

    #     raw_orderbook = self._get_orderbook_from_api_resp(req)
        # parsed_orderbook = self.parse_orderbook(raw_orderbook, volume_limit)
        # parsed_orderbook['time_parsed'] = Delorean().epoch

        # return parsed_orderbook
        
    def place_order_req(self, mode, volume, price=None, order_type=order_types.LIMIT_ORDER):
        """
            Place Order
            This costs, gas, don't do this so often if one can help it.
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
        
        self.load_creds()

        self.base = ''

        if self.network == 'mainnet':
            self.base = self.bamboo_main_base_url
        else:
            self.base = self.bamboo_test_base_url 
        
        self.open_orders_url = '/accounts/%s/orders' % self.api_key # eth addr
        url = self.base + self.open_orders_url
        
        return self.req(
            'get',
            url,
        )


    def get_open_orders_resp(self, req):
        """
        Get Details of an order
        """
        raw_orders = self.resp(req)
        orders = []

        for raw_order in raw_orders:
            if raw_order['state'] == 'OPEN':
                
                mode = self._order_mode_to_const(raw_order['type'])
                vol = Decimal(raw_order['signedOrder']['makerAssetAmount'])/1000000000000000000
                volume = Money(vol, self.volume_currency)

                order = {
                    'mode': mode,
                    'id': '%s' % raw_order['orderHash'],
                    'price': Money(raw_order['price'], self.currency),
                    'volume': volume,
                    'volume_remaining': Money(raw_order['remainingBaseTokenAmount'], self.volume_currency),
                    'status': raw_order['state'],
                }
                orders.append(order)

        return orders

    def get_order_details(self, order_id):
        oid = '%s' % order_id # Order Hash
        req = self.get_order_details_req(oid)
        return self.get_order_details_resp(req, oid)

    def get_order_details_req(self, order_id):
        """
            OrderHash is used as OrderID, retrieves details.
        """
        self.load_creds()

        self.base = ''

        if self.network == 'mainnet':
            self.base = self.bamboo_main_base_url
        else:
            self.base = self.bamboo_test_base_url 
        
        self.order_details_url = '/orders/%s' % order_id # eth addr
        details_url = self.base + self.order_details_url
        
        return self.req(
            'get',
            details_url,
            # no_auth=False,
            # verify=verify,
            # params=payload,
        )


    def get_order_details_resp(self, req, order_id):
        """
            Get Order Details Response
        """
        order_details = self.resp(req)
        oid = '%s' % order_details["orderHash"]
        # print(order_details)

        side = self._order_mode_to_const(order_details["type"])

        # 🚧🚧🚧 TODO: this is wrong, it is remainingVol, it should be what is left to fill (eth)
        total_volume_currency = order_details["remainingBaseTokenAmount"]
        vol_currency_final = Money(total_volume_currency, self.volume_currency)
        
        # 🚧🚧🚧 TODO: similar as above but with DAI
        total_price_currency = '%.2f' % Decimal(order_details["remainingQuoteTokenAmount"])
        
        # 🚧🚧🚧 TODO: similar as above but with DAI
        time_created = round(Decimal(order_details["createdTimestamp"]) / Decimal(1000))

        data = {
            'time_created': time_created,
            'type': side,
            '%s_total' % self.volume_currency.lower(): vol_currency_final,
            'fiat_total': Money(total_price_currency, self.currency),
            'trades': [],
        }
        print(order_details)
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
                    'trade_id': str(trade['orderId']),  # none given by Binance F
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


    def parse_order(self, order):
        price = Money(order[0], self.currency)
        volume = Money(order[1], self.volume_currency)

        return price, volume
    
    
    
    @property
    def _orderbook_sort_key(self):

        return lambda order: float(order[0])
        
    def parse_orderbook(self, raw_orderbook, volume_limit=None, price_limit=None, cached_orders=False):
        """
        Returns a dictionary containing a sorted list of asks and a sorted list of bids.
        """

        # if cached_orders:
        #     raw_bids = raw_orderbook['bids']
        #     raw_asks = raw_orderbook['asks']
        #     sort_key = lambda o: float(o[0])
        # else:
        raw_bids = self._get_raw_bids(raw_orderbook)
        raw_asks = self._get_raw_asks(raw_orderbook)
        sort_key = self._orderbook_sort_key
        print("raw bids==============================================")
        print(raw_bids)
        print("raw bids==============================================")

        raw_bids.sort(key=sort_key, reverse=True)
        raw_asks.sort(key=sort_key)

        bids = []
        asks = []

        total_volume = Money(0, self.volume_currency)
        top_bid_price, _ = self.parse_any_order(raw_bids[0], cached_orders)

        for bid in raw_bids:
            bid_price, bid_volume = self.parse_any_order(bid, cached_orders)

            if price_limit:
                bid_threshold = top_bid_price - price_limit

                if bid_price < bid_threshold:
                    break

            bids.append(Order(bid_price, bid_volume, self, Order.BID))

            total_volume += bid_volume

            if volume_limit and total_volume > volume_limit:
                break

        total_volume = Money('0', self.volume_currency)
        top_ask_price, __ = self.parse_any_order(raw_asks[0], cached_orders)

        for ask in raw_asks:
            ask_price, ask_volume = self.parse_any_order(ask, cached_orders)

            if price_limit:
                ask_threshold = top_ask_price + price_limit

                if ask_price > ask_threshold:
                    break

            asks.append(Order(ask_price, ask_volume, self, Order.ASK))

            total_volume += ask_volume

            if volume_limit and total_volume > volume_limit:
                break

        return {'bids': bids, 'asks': asks}
    
            
    # this is a utility used when formulating eth_calls
    def sub_bytes(self, i, start=0, end=0):
        i_str = i 
        i_sub = i_str[-end * 2: len(i_str) - start * 2]  # get the bytes we need
        return hex(int(i_sub or '0', 16))  # convert to back int ..or not