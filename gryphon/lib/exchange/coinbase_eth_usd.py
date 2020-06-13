from gryphon.lib.exchange.coinbase_btc_usd import CoinbaseBTCUSDExchange
from gryphon.lib.logger import get_logger
from gryphon.lib.money import Money

logger = get_logger(__name__)


class CoinbaseETHUSDExchange(CoinbaseBTCUSDExchange):
    def __init__(self, session=None, use_cached_orderbook=False):
        super(CoinbaseETHUSDExchange, self).__init__(session)
        self.name = u'COINBASE_ETH_USD'
        self.friendly_name = u'Coinbase ETH-USD'
        self.base_url = 'https://api.exchange.coinbase.com'
        self.currency = 'USD'
        self.volume_currency = 'ETH'
        self.use_cached_orderbook = use_cached_orderbook
        self.product_id = 'ETH-USD'

    def load_creds(self):
        try:
            self.api_key
            self.secret
            self.passphrase
        except AttributeError:
            self.api_key = self.load_env('COINBASE_ETH_USD_API_KEY')
            self.passphrase = self.load_env('COINBASE_ETH_USD_API_PASSPHRASE')
            self.secret = self.load_env('COINBASE_ETH_USD_API_SECRET')

    def load_wallet_creds(self):
        try:
            self.wallet_api_key
            self.wallet_api_secret
            self.wallet_id
        except AttributeError:
            self.wallet_api_key = self.load_env('COINBASE_ETH_USD_WALLET_API_KEY')
            self.wallet_api_secret = self.load_env('COINBASE_ETH_USD_WALLET_API_SECRET')
            self.wallet_id = self.load_env('COINBASE_ETH_USD_WALLET_ID')

    def load_fiat_account_id(self):
        return self.load_env('COINBASE_ETH_USD_FIAT_ACCOUNT_ID')

    def fiat_deposit_fee(self, deposit_amount):
        return Money('1', 'USD')
