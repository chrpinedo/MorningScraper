import sys
import re
import abc
import six
from decimal import Decimal
from datetime import datetime

from bs4 import BeautifulSoup

if sys.version_info[0] == 3:
    from urllib.request import urlopen
elif sys.version_info[0] == 2:
    from urllib import urlopen
else:
    raise Exception('Python version 2 or 3 required')


def make_soup(url, parser="html.parser"):
    response = urlopen(url)
    soup = BeautifulSoup(response, parser)
    return soup


@six.add_metaclass(abc.ABCMeta)
class SecurityPage(object):

    @classmethod
    def from_url(cls, url):
        if '/uk/funds/snapshot/snapshot' in url:
            return FundsPage(url)
        elif '/uk/stockreport/' in url:
            return StockPage(url)
        elif '/uk/etf/' in url:
            return ETFPage(url)

    def __init__(self, url):
        self.url = url
        cls_name = self.__class__.__name__
        security_type = cls_name[:cls_name.find("Page")]
        self.data_ = {"type": security_type, "url": self.url}

    def get_data(self):
        soup = make_soup(self.url)
        self._update_data(soup)
        return self.data_

    @abc.abstractmethod
    def _update_data(self, soup):
        """"""


class FundsPage(SecurityPage):
    """
    http://www.morningstar.co.uk/uk/funds/snapshot/snapshot.aspx?id=F00000NGEH
    """
    def _update_data(self, soup):
        text = soup.find_all('div', class_='snapshotTitleBox')[0].h1.text
        self.data_["name"] = str(text)
        table = soup.find_all('table', class_='overviewKeyStatsTable')[0]
        for tr in table.find_all('tr'):
            tds = tr.find_all('td')
            if len(tds) != 3:
                continue
            if tds[0].text.startswith('NAV'):
                date = tds[0].span.text
                (currency, value) = tds[2].text.split()
            if tds[0].text.startswith('Day Change'):
                change = tds[2].text.strip()
            if tds[0].text.startswith('ISIN'):
                isin = tds[2].text.strip()
        result = {
            'value': Decimal(value),
            'currency': currency,
            'change': change,
            'date': datetime.strptime(date, '%d/%m/%Y').date(),
            'ISIN': isin
        }
        self.data_.update(result)


class StockPage(SecurityPage):
    def _update_data(self, soup):
        title = soup.find_all('span', class_='securityName')[0].text
        value = soup.find_all('span', id='Col0Price')[0].text
        change = soup.find_all('span', id='Col0PriceDetail')[0].text
        change = change.split('|')[1].strip()
        date = soup.find_all('p', id='Col0PriceTime')[0].text[6:16]
        currency = soup.find_all('p', id='Col0PriceTime')[0].text
        currency = re.search(r'\|\s([A-Z]{3,4})\b', currency).group(1)
        isin = soup.find_all('td', id='Col0Isin')[0].text
        return {
            'name': title,
            'value': Decimal(value),
            'currency': currency,
            'change': change,
            'date': datetime.strptime(date, '%d/%m/%Y').date(),
            'ISIN': isin
        }


class ETFPage(SecurityPage):
    def _update_data(self, soup):
        text = soup.find_all('div', class_='snapshotTitleBox')[0].h1.text
        self.data_["name"] = text.split('|')[0].strip()
        self.data_["ticker"] = text.split('|')[1].strip()
        for keyword in ["Exchange", "ISIN"]:
            line = soup.find(text=keyword)
            if line is None:
                continue
            text = line.parent.nextSibling.nextSibling.text
            self.data_[keyword] = str(text)
        line = soup.find(text="Closing Price")
        if line is not None:
            self.data_["currency"] = \
                line.parent.nextSibling.nextSibling.text[:3]
