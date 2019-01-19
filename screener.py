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
    try:
        return float(number.replace(',', ''))
    except ValueError:
        return 0


class Screener:
    def __init__(self, markets):
        assert all(
            'output_file' in market and 'company_list' in market and 'url_template' in market
            for market in markets)
        self.markets = markets
        self.metrics = collections.defaultdict(lambda: 0)

    def fetch_data_from_url(self, url, cache=True):
        print('Fetching URL: %s ...' % url)
        r = requests.get(url)
        if r.status_code != 200:
            self.metrics['FailedRequests'] += 1
            raise Exception('Failed request. Skipping %s' % url)
        text = r.content.decode('utf-8-sig')  # Byte order mark being returned
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
            if sector and sector[0]:
                self.file_cache[cache_key] = sector[0].text
                return sector
            else:
                raise Exception('Sector could not be found from %s' % url)

    def convert_to_table(self, companies):
        table = []
        table.append(['Symbol', 'Name', 'Sector', 'OM', 'FCFM', 'ROA', 'ROE', 'PScore',
                      'CR', 'D/E', 'Revenue', 'YEG', 'YRG', 'EPS', 'BPS', 'DPS'])
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
            row.append(data.get('earnings_per_share', 0))
            row.append(data.get('book_value_per_share', 0))
            row.append(data.get('dividends_per_share', 0))
            table.append(row)
        return table

    def pretty_print_table(self, companies):
        table = PrettyTable()
        data = self.convert_to_table(companies)
        table.field_names = data[0]
        for row in data[1:]:
            table.add_row(row)
        print(table)

    def save_to_csv(self, companies, output_filename):
        data = self.convert_to_table(companies)
        with open(output_filename, 'w', newline='\n') as output_file:
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
            ttm_data = _parse_number(row[-1])
            if header == 'Operating Margin':
                data['operating_margin'] = ttm_data / 100
            elif header == 'Free Cash Flow/Sales %':
                data['free_cash_flow_margin'] = ttm_data / 100
            elif header.startswith('Earnings Per Share '):
                data['earnings_per_share'] = ttm_data
            elif header.startswith('Dividends '):
                data['dividends_per_share'] = ttm_data
            elif header.startswith('Book Value Per Share * '):
                data['book_value_per_share'] = ttm_data
            elif header.startswith('Revenue ') and header.endswith(' Mil'):
                data['revenue'] = ttm_data * 1000000
            elif header == 'Return on Assets %':
                data['return_on_assets'] = ttm_data / 100
            elif header == 'Return on Equity %':
                data['return_on_equity'] = ttm_data / 100
            elif header == 'Current Ratio':
                data['current_ratio'] = ttm_data
            elif header == 'Debt/Equity':
                data['debt_to_equity_ratio'] = ttm_data
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

        print('Finished processing %s' % ticker)
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
                self.save_to_csv(companies, market['output_file'])
        print('Metrics: %s' % dict(self.metrics))


if __name__ == '__main__':
    Screener(config.MARKETS).import_data()
