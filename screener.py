#!/usr/bin/env python
import collections
import csv
import io
import requests
import shelve
import traceback
from bs4 import BeautifulSoup
from prettytable import PrettyTable
import config


def _parse_number(number):
    if not number:
        return 0
    if number[-1] == 'M':
        return _parse_number(number[:-1]) * 1000000
    elif number[-1] == 'B':
        return _parse_number(number[:-1]) * 1000000000
    elif number.count('.') >= 2 and number.count(',') <= 1:
        # Brazilian standard, dot is a thousand separator, not a decimal one
        return float(number.replace('.', '').replace(',', '.'))
    else:
        return float(number.replace(',', ''))


class Screener:
    def __init__(self, markets):
        assert all(
            'output_file' in market and 'company_list' in market and
            'url_template' in market and 'profile_url_template' in market and
            'share_count' in market and 'url_template' in market['share_count'] and
            'selector' in market['share_count']
            for market in markets)
        self.markets = markets
        self.metrics = collections.defaultdict(lambda: 0)

    def fetch_data_from_url(self, url, cache=True):
        print('Fetching URL: %s ...' % url)
        headers = {}
        if 'fundamentus' in url:  # Somehow this works to prevent receiving a bad HTTP 302
            headers['Cookie'] = 'PHPSESSID'
        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            self.metrics['FailedRequests'] += 1
            raise Exception('Failed request. Skipping %s' % url)
        try:
            text = r.content.decode('utf-8-sig')  # Byte order mark being returned
        except UnicodeDecodeError:
            text = r.text
        if not text:
            self.metrics['EmptyRequests'] += 1
            raise Exception('Empty response from server. Skipping %s' % url )
        print('Finished fetching URL: %s' % url)
        if cache:
            self.file_cache[url] = text
            print('Saved URL into the cache file: %s' % url)
        self.metrics['SuccessfulRequests'] += 1
        return text

    def fetch_data(self, url):
        if url in self.file_cache:
            self.metrics['CacheHit'] += 1
            return self.file_cache[url]
        else:
            self.metrics['CacheMiss'] += 1
            return self.fetch_data_from_url(url)

    def fetch_sector_data(self, url):
        cache_key = 'sector__%s' % url
        if cache_key in self.file_cache:
            self.metrics['CacheHit'] += 1
            return self.file_cache[cache_key]
        else:
            self.metrics['CacheMiss'] += 1
            raw_text = self.fetch_data_from_url(url, cache=False)
            soup = BeautifulSoup(raw_text, 'lxml')
            sector = soup.select(
                '#Col1-3-Profile-Proxy > section > div.asset-profile-container > div > div > '
                'p.D\\28 ib\\29.Va\\28 t\\29 > strong:nth-child(2)')
            if not sector or not sector[0]:
                sector = soup.select(
                    '#Col1-0-Profile-Proxy > section > div.asset-profile-container > div > div > '
                    'p.D\\28 ib\\29.Va\\28 t\\29 > strong:nth-child(2)')
            if sector and sector[0]:
                self.file_cache[cache_key] = sector[0].text
                return sector
            else:
                raise Exception('Sector could not be found from %s' % url)

    def fetch_share_count_data(self, share_count_source, ticker):
        url = share_count_source['url_template'](ticker)
        cache_key = 'share_count__%s' % url
        if cache_key in self.file_cache:
            self.metrics['CacheHit'] += 1
            return self.file_cache[cache_key]
        else:
            self.metrics['CacheMiss'] += 1
            raw_text = self.fetch_data_from_url(url, cache=False)
            soup = BeautifulSoup(raw_text, 'lxml')
            share_count_text = soup.select(share_count_source['selector'])
            if share_count_text and share_count_text[0]:
                share_count = _parse_number(share_count_text[0].text)
                if share_count == 0:
                    raise Exception('Share count was invalid found from %s' % url)
                self.file_cache[cache_key] = share_count
                return share_count
            else:
                raise Exception('Share count could not be found from %s' % url)

    def convert_to_table(self, companies, fields):
        table = []
        if fields:
            table.append(fields)
        else:
            table.append(['Symbol', 'Name', 'Sector', 'OM', 'FCFM', 'ROA', 'ROE', 'PScore',
                          'CR', 'D/E', 'Revenue', 'YEG', 'YRG', 'EPS', 'RPS', 'BPS', 'DPS'])
        for (company, data) in companies.items():
            row = []
            row.append(company)
            row.append(data.get('name', '').replace('Real Estate Investment Trust', 'REIT'))
            row.append(data.get('sector', ''))
            row.append(data.get('operating_margin', 0))
            row.append(data.get('free_cash_flow_margin', 0))
            row.append(data.get('return_on_assets', 0))
            row.append(data.get('return_on_equity', 0))
            row.append(1000 * data.get('operating_margin', 0) *
                       data.get('free_cash_flow_margin', 0) *
                       data.get('return_on_assets', 0) *
                       data.get('return_on_equity', 0))
            row.append(data.get('current_ratio', 0))
            row.append(data.get('debt_to_equity_ratio', 0))
            row.append(data.get('revenue', 0))
            row.append(min(
                data.get('earnings_growth_3y', 0),
                data.get('earnings_growth_5y', 0))),
            row.append(min(
                data.get('revenue_growth_3y', 0),
                data.get('revenue_growth_5y', 0))),
            earnings_per_share = data.get('net_income', 0) / data.get('share_count')
            revenue_per_share = data.get('revenue', 0) / data.get('share_count')
            row.append(earnings_per_share)
            row.append(revenue_per_share)
            row.append(data.get('book_value_per_share', 0))
            row.append(data.get('dividends_per_share', 0))
            table.append(row)
        return table

    def pretty_print_table(self, companies, market):
        table = PrettyTable()
        fields = market.get('i18n_fields', None)
        data = self.convert_to_table(companies, fields)
        table.field_names = data[0]
        for row in data[1:]:
            table.add_row(row)
        print(table)

    def save_to_csv(self, companies, market):
        output_filename = market['output_file']
        fields = market.get('i18n_fields', None)
        data = self.convert_to_table(companies, fields)
        with open(output_filename, 'w', newline='\n', encoding='utf-8') as output_file:
            csv.writer(output_file, lineterminator='\n').writerows(data)

    def import_data_morningstar(self, ticker, market):
        raw_data = self.fetch_data(market['url_template'](ticker))
        raw_data_table = csv.reader(io.StringIO(raw_data))
        data = {}
        current_state = ''
        for row in raw_data_table:
            if not row:
                continue
            header = row[0]
            if header and not any(row[1:-1]):
                name_line = 'Growth Profitability and Financial Ratios for '
                if header.startswith(name_line):
                    data['name'] = header.split(name_line)[1]
                else:
                    current_state = header
                continue
            ttm_data = lambda: _parse_number(row[-1])
            if header == 'Operating Margin':
                data['operating_margin'] = ttm_data() / 100
            elif header == 'Free Cash Flow/Sales %':
                data['free_cash_flow_margin'] = ttm_data() / 100
            elif header.startswith('Dividends '):
                data['dividends_per_share'] = ttm_data()
            elif header.startswith('Book Value Per Share * '):
                data['book_value_per_share'] = ttm_data()
            elif header.startswith('Net Income ') and header.endswith(' Mil'):
                data['net_income'] = ttm_data() * 1000000
            elif header.startswith('Revenue ') and header.endswith(' Mil'):
                data['revenue'] = ttm_data() * 1000000
            elif header == 'Return on Assets %':
                data['return_on_assets'] = ttm_data() / 100
            elif header == 'Return on Equity %':
                data['return_on_equity'] = ttm_data() / 100
            elif header == 'Current Ratio':
                data['current_ratio'] = ttm_data()
            elif header == 'Debt/Equity':
                data['debt_to_equity_ratio'] = ttm_data()
            elif header == '5-Year Average':
                if current_state == 'Revenue %':
                    data['revenue_growth_5y'] = _parse_number(row[-2]) / 100
                elif current_state == 'Net Income %':
                    data['earnings_growth_5y'] = _parse_number(row[-2]) / 100
            elif header == '3-Year Average':
                if current_state == 'Revenue %':
                    data['revenue_growth_3y'] = _parse_number(row[-2]) / 100
                elif current_state == 'Net Income %':
                    data['earnings_growth_3y'] = _parse_number(row[-2]) / 100

        data['sector'] = self.fetch_sector_data(market['profile_url_template'](ticker))
        data['share_count'] = self.fetch_share_count_data(market['share_count'], ticker)

        self.metrics['ProcessedCompanies'] += 1
        return data

    def import_data(self):
        with shelve.open('screener_cache') as file_cache:
            self.file_cache = file_cache
            for market in self.markets:
                companies = {}
                for ticker in market['company_list']:
                    try:
                        companies[ticker] = self.import_data_morningstar(ticker, market)
                    except:
                        self.metrics['FailedToProcessCompany'] += 1
                        print('Failed to process company %s' % ticker)
                        traceback.print_exc()
                self.save_to_csv(companies, market)
        print('Metrics: %s' % dict(self.metrics))


if __name__ == '__main__':
    Screener(config.MARKETS).import_data()
