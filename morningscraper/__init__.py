import sys
import re

from decimal import Decimal
from datetime import datetime

from bs4 import BeautifulSoup

from security import make_soup, SecurityPage


if sys.version_info[0] == 3:
    from urllib.request import urlopen
    from urllib.parse import quote, urlsplit
elif sys.version_info[0] == 2:
    from urllib import urlopen, quote
    from urlparse import urlsplit
else:
    raise Exception('Python version 2 or 3 required')

SITE = 'morningstar.co.uk'
SITE_BASE = 'http://www.' + SITE
SEARCH_BASE = SITE_BASE + '/uk/funds/SecuritySearchResults.aspx?search=%s'


def dmy_2_date(value):
    ''' Convert dd/mm/yyyy date string into python date '''
    return datetime.strptime(value, '%d/%m/%Y').date()


def fix_url(url):
    ''' Fully qualify url if domain missing '''
    if url.startswith('/'):
        url = SITE_BASE + url
    return url


def search(ref, verbose=False):
    ''' Search morningstar.co.uk for ref

        If ref is found and is a fund or stock return details

        .. warning:: This only retrieves the first few funds/stocks found

        Args:
            ref (str): search term can be ISIN or search term
            verbose (bool): provide output

        Returns:

            list: list containing dict for each found entry


            **dict for stock:**

            .. code::

                {
                    'name': (str) name of stock
                    'url': (str) url for stock info
                    'type': (str) 'Stock'
                    'ticker': (str) ticker name
                    'currency': (str) currency code of stock
                }

            **dict for fund:**

            .. code::

                {
                    'name': (str) name of fund
                    'url': (str) url for fund info
                    'type': (str) 'Fund'
                    'ISIN': (str) ISIN of fund
                }
    '''

    if verbose:
        print('Search for: %s' % ref)
    parsed_html = make_soup(SEARCH_BASE % quote(ref))
    results = []
    stocks = parsed_html.find_all(
        'table', id='ctl00_MainContent_stockTable'
    )
    if stocks:
        stocks = stocks[0].find_all('tr')[1:]
        for stock in stocks:
            results.append({
                'name': stock.td.text,
                'url': fix_url(stock.td.a.get('href')),
                'type': 'Stock',
                'ticker': stock.find_all('td', class_='searchTicker')[0].text,
                'currency': stock.find_all(
                    'td', class_='searchCurrency'
                )[0].text,
            })

    for instrument_type in ["fund", "etf"]:
        funds = parsed_html.find_all(
            'table', id='ctl00_MainContent_{}Table'.format(instrument_type)
        )
        if funds:
            funds = funds[0].find_all('tr')[1:]
            for fund in funds:
                data = fund.find_all('td')
                results.append({
                    'name': data[0].text,
                    'url': fix_url(data[0].a.get('href')),
                    'type': instrument_type,
                    'ISIN': data[1].text,
                })
            break

    if verbose:
        if results:
            print('%s item(s) found.' % len(results))
            for item in results:
                print(item)
        else:
            print('No items found.')
    return results


def get_data(ref, verbose=False):
    ''' Search morningstar.co.uk for ref

        If ref is found return details for each fund/stock

        Args:
            ref (str): search term can be ISIN or search term
            verbose (bool): provide outpuss

        Returns:
            list: list containing dict for each found entry

            .. code::

                [{
                    'name': (str) name of the fund/stock
                    'ISIN': (str) ISIN reference for the fund/stock
                    'date': (Date) date of valuation
                    'value': (Decimal) value of the fund/stock
                    'currency': (str) currency e.g. GBP USD
                    'change': (str) percent change, including %
                    'type': (str) e.g. Fund Stock
                    'url': (str) fully qualified url info gathered from
                }, ...]

    '''
    results = search(ref, verbose=verbose)
    output = []
    for item in results:
        data = get_url(item['url'], verbose=verbose)
        if data:
            output.append(data)
    return output


def get_url(url, verbose=False):
    ''' open morningstar.co.uk url and return details

        Args:
            url (str): url to parse
            verbose (bool): provide output

        Returns:
            dict: list containing fund/stock info

            .. code::

                {
                    'name': (str) name of the fund/stock
                    'ISIN': (str) ISIN reference for the fund/stock
                    'date': (Date) date of valuation
                    'value': (Decimal) value of the fund/stock
                    'currency': (str) currency e.g. GBP USD
                    'change': (str) percent change, including %
                    'type': (str) e.g. Fund Stock
                    'url': (str) fully qualified url info gathered from
                }
    '''
    if verbose:
        print('\nOpening %s' % url)
    if not urlsplit(url).netloc.endswith(SITE):
        raise Exception('Non morningstar.co.uk url %r' % url)
    page = SecurityPage.from_url(url)
    result = page.get_data()
    if verbose:
        print(result)
    return result


if __name__ == '__main__':
    # search('EWJ', verbose=True)
    get_data('EWJ', verbose=True)
    get_data('GB00B54RK123', verbose=True)
    get_data('LLOY LSE', verbose=True)
    get_data('GOOG NASDAQ', verbose=True)
    get_data('LU1023728089', verbose=True)
