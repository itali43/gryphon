"""
Mirror one exchange and make on another, another can be empty
"""

from cdecimal import Decimal

from gryphon.execution.strategies.base import Strategy
from gryphon.execution.strategies.builtin.fundamental_value import native as native_midpoint
from gryphon.lib import configuration as configuration_lib
from gryphon.lib.money import Money
from gryphon.lib.exchange import exceptions as exchange_exceptions
from gryphon.lib.exchange.consts import Consts
from gryphon.lib.order_sliding import slide_order


class Mirror(Strategy):
    def __init__(self, db, harness, strategy_configuration=None):
        super(Mirror, self).__init__(db, harness)

        # Immutable properties.
        self.volume_currency = 'BTC'
        self.exchange_name = 'BITSTAMP_BTC_USD'
        self._actor = 'MIRROR'  

        # Configurable properties with defaults.
        self.target_exchange = None

        self.trusted_exchanges = []

        self.spread = Decimal('0.10')
        self.base_volume = Money('0.005', 'BTC')
        self.max_position = Money('0.5', 'BTC')
        self.fundamental_depth = Money('5', 'BTC')
        self.primary_exchange_name = None
        self.fundamental_exchange_names = None
        self.midpoint_weights = None
        self.use_variable_sizing = False
        self.variable_sizing_spread = Decimal('0.03')
        self.variable_sizing_multiplier = Decimal('2')
        self.slide_jump = Money('0.01', 'USD')
        self.slide_ignore_volume = Money('0.00000001', 'BTC')
        self.max_spread = Money('1000', 'USD')

        self.refresh_order_tick = 0

        if strategy_configuration:
            self.configure(strategy_configuration)

    def configure(self, strategy_configuration):
        super(Mirror, self).configure(strategy_configuration)

        self.init_configurable('midpoint_weights', strategy_configuration)
        self.init_configurable('use_variable_sizing', strategy_configuration)
        self.init_configurable('variable_sizing_spread', strategy_configuration)
        self.init_configurable('variable_sizing_multiplier', strategy_configuration)
        self.init_configurable('slide_jump', strategy_configuration)




        self.init_configurable('spread', strategy_configuration)
        self.init_configurable('base_volume', strategy_configuration)
        self.init_configurable('max_position', strategy_configuration)
        self.init_configurable('fundamental_depth', strategy_configuration)
        self.init_configurable('primary_exchange_name', strategy_configuration)
        self.init_configurable('fundamental_exchange_names', strategy_configuration)
        
        self.init_configurable('refresh_order_tick', strategy_configuration)

        self.init_primary_exchange()
        self.init_fundamental_exchanges()

        # self.validate_configuration()

    # def validate_configuration(self):
    #     assert sum(self.midpoint_weights.values()) == Decimal('1')

    def init_primary_exchange(self):
        self.primary_exchange = self.harness.exchange_from_key(
            self.primary_exchange_name,
        )

        # This causes us to always audit our primary exchange.
        self.target_exchanges = [self.primary_exchange.name]

    def init_fundamental_exchanges(self):
        self.fundamental_exchange_names = configuration_lib.parse_configurable_as_list(
            self.fundamental_exchange_names,
        )

        self.fundamental_exchanges = [
            self.harness.exchange_from_key(exchange_name)
            for exchange_name in self.fundamental_exchange_names
        ]

    def get_all_orderbooks(self):
        orderbooks = {}

        for exchange in self.fundamental_exchanges:
            ob = exchange.get_orderbook()
            orderbooks[exchange.name] = ob

        return orderbooks

    def calculate_global_midpoint(self, orderbooks):
        """
        Unweighted average of the midpoints.

        TODO features:
            - count failures

        TODO Iterations:
            - midpoint of the global orderbook
            - incorporate balance into this calculation
        """
        total = Decimal('0')
        final_midpoint = 0

        for exchange_name, orderbook in orderbooks.items():
            ob_midpoint = native_midpoint.calculate(orderbook, self.fundamental_depth)
            final_midpoint += self.midpoint_weights[exchange_name.lower()] * ob_midpoint

        midpoint = total / len(orderbooks)

        return final_midpoint

    def tick(self, current_orders):
        """
        V0.5:
            For a configurable exchange:
            For a list of exchange orderbooks to consider
            Get the orderbooks.
            Calculate the weighted global midpoint.
            Calculate the prices at a fixed spread from the midpoint.
            Calculate the volumes, given the prices, position, and max position.
            Increase the volumes if we can place our orders at a very wide spread.
            Place the orders.
        """
        self.refresh_order_tick += 1
        

        if self.refresh_order_tick == 10:
            self.harness.log('refresh!', color='cyan')
            self.primary_exchange.cancel_all_open_orders() # TODO: primary?

        # bid_extra_data = {}
        # ask_extra_data = {}

        orderbooks = self.get_all_orderbooks()
        # midpoint = self.calculate_global_midpoint(orderbooks)

        ask_to_mirror = orderbooks[self.primary_exchange.name]['asks'][0]
        bid_to_mirror = orderbooks[self.primary_exchange.name]['bids'][0]


        self.harness.log('%s, %s' % (ask_to_mirror, bid_to_mirror), color='green')
        self.harness.log('second best, (a, b):', color='red')
        self.harness.log('%s, %s' % (orderbooks[self.primary_exchange.name]['asks'][1], orderbooks[self.primary_exchange.name]['bids'][1]), color='red')

        # bid_price = midpoint - (midpoint * self.spread)
        # ask_price = midpoint + (midpoint * self.spread)

        # bid_extra_data['fundamental_value'] = midpoint
        # ask_extra_data['fundamental_value'] = midpoint

        # bid_price = slide_order(
        #     Consts.BID,
        #     bid_price,
        #     orderbooks[self.primary_exchange.name],
        #     self.slide_ignore_volume,
        #     self.slide_jump,
        #     self.max_spread / 2,
        # )

        # ask_price = slide_order(
        #     Consts.ASK,
        #     ask_price,
        #     orderbooks[self.primary_exchange.name],
        #     self.slide_ignore_volume,
        #     self.slide_jump,
        #     self.max_spread / 2,
        # )

        # bid_volume, bid_extra_data, ask_volume, ask_extra_data = self.calculate_volumes(
        #     midpoint,
        #     bid_price,
        #     ask_price,
        #     bid_extra_data,
        #     ask_extra_data,
        # )

        # if bid_volume > 0:
        #     try:
        #         self.primary_exchange.limit_order(
        #             Consts.BID,
        #             bid_volume,
        #             bid_price,
        #             extra_data=bid_extra_data,
        #         )
        #     except exchange_exceptions.InsufficientFundsError:
        #         self.harness.log('Insuff funds error, skipping', color='red')

        # if ask_volume > 0:
        #     try:
        #         self.primary_exchange.limit_order(
        #             Consts.ASK,
        #             ask_volume,
        #             ask_price,
        #             extra_data=ask_extra_data,
        #         )
        #     except exchange_exceptions.InsufficientFundsError:
        #         self.harness.log('Insuff funds error, skipping', color='red')

    def calculate_base_volumes(self):
        """
        We place orders of size [base_volume] unless we are within [base_volume] of our
        max position on that size. In that case, we only place the difference between
        our [current position] and [max_position].
        """
        bid_volume = self.base_volume
        ask_volume = self.base_volume

        if (self.position + self.base_volume) > self.max_position:
            bid_volume = self.max_position - self.position

        if (self.position - self.base_volume) < -self.max_position:
            ask_volume = self.max_position + self.position

        return bid_volume, ask_volume

    def calculate_volumes(self, midpoint, bid_price, ask_price, bid_extra_data, ask_extra_data):
        bid_volume, ask_volume = self.calculate_base_volumes()

        if self.use_variable_sizing is True:
            bid_volume, bid_extra_data = self.apply_variable_sizing(
                Consts.BID,
                bid_volume,
                bid_price,
                midpoint,
                bid_extra_data,
            )

            ask_volume, ask_extra_data = self.apply_variable_sizing(
                Consts.ASK,
                ask_volume,
                ask_price,
                midpoint,
                ask_extra_data,
            )

        return bid_volume, bid_extra_data, ask_volume, ask_extra_data

    def apply_variable_sizing(self, side, order_volume, price, midpoint, extra_data):
        initial_volume = order_volume
        real_spread = None

        if side == Consts.BID:
            real_spread = midpoint / price
        elif side == Consts.ASK:
            real_spread = price / midpoint

        if (real_spread - 1) > self.variable_sizing_spread:
            order_volume = order_volume * self.variable_sizing_multiplier

            extra_data['variable_sizing_volume'] = order_volume - initial_volume

        return order_volume, extra_data

    def mid_tick_logging(self, midpoint, bid_price, ask_price):
        self.harness.log('Prospective bid: '.ljust(20) + str(bid_price), color='blue')
        self.harness.log('Midpoint: '.ljust(20) + str(midpoint), color='blue')
        self.harness.log('Prospective ask: '.ljust(20) + str(ask_price), color='blue')