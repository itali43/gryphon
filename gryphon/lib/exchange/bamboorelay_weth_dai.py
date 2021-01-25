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
from operator import itemgetter

from gryphon.lib.exchange import exceptions
from gryphon.lib.exchange import order_types
from gryphon.lib.exchange.exchange_api_wrapper import ExchangeAPIWrapper
from gryphon.lib.logger import get_logger
from gryphon.lib.models.exchange import Balance
from gryphon.lib.money import Money
from gryphon.lib.time_parsing import parse

logger = get_logger(__name__)


class BambooETHDAIExchange(ExchangeAPIWrapper):
    def __init__(self, session=None, configuration=None):
        super(BambooETHDAIExchange, self).__init__(session)

        self.name = u'BAMBOO_ETH_DAI'
        self.friendly_name = u'Bamboo ETH-DAI'
        self.base_url = 'https://rest.bamboorelay.com/main/0x/'
        self.test_base_url = 'https://rest.bamboorelay.com/ropsten/0x/'

        self.currency = 'DAI'
        self.currency_symbol = 'DAI'  # TODO: Recheck/refactor
        self.volume_currency = 'ETH'
        self.bid_string = 'BUY'
        self.ask_string = 'SELL'
        self.nonce = 1
        self.ticker_symbols = 'ETH'

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

        self.ping_url = '/wapi/v3/systemStatus.html'
        self.balance_url = '/sapi/v1/accountSnapshot' 

        self.market_depth_url = '/depth'
        self.ticker_url = '/ticker/24hr'
        self.orderbook_url = '/depth'
        self.position_url = '/positionRisk'
        self.trades_url = '/userTrades'
        self.order_url = '/order'
        self.open_orders_url = '/openOrders'
        self.transactions_url = '/allOrders'

        if configuration:
            self.configure(configuration)

    # Request implementation methods.

    def auth_request(self, req_method, url, request_args):

        self.transactions_url = '/allOrders'













