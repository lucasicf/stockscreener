#!/usr/bin/env python
import collections
import csv
import io
import prettytable
import requests
import shelve


URL_CANADA = lambda ticker: "http://financials.morningstar.com/ajax/exportKR2CSV.html?t=" + ticker + "&culture=en-CA&region=CAN"


def _parse_number(number):
    try:
        return float(number.replace(',', ''))
    except ValueError:
        return 0


class Screener:
    def __init__(self):
        self.metrics = collections.defaultdict(lambda: 0)
        self.companies = collections.defaultdict(dict)

    def fetch_data_from_url(self, url):
        r = requests.get(url)
        if r.status_code != 200:
            self.metrics['FailedRequests'] += 1
            raise
        text = r.content.decode('utf-8-sig')  # Byte order mark being returned
        self.file_cache[url] = text
        return text

    def fetch_data(self, url):
        if url in self.file_cache:
            self.metrics['CacheHit'] += 1
            text = self.file_cache[url]
            if not text:
                self.metrics['CorruptedCache'] += 1
                text = self.fetch_data_from_url(url)
        else:
            self.metrics['CacheMiss'] += 1
            text = self.fetch_data_from_url(url)
        return csv.reader(io.StringIO(text))

    def convert_to_table(self):
        table = []
        table.append(['Symbol', 'Name', 'Sector', 'OM', 'FCFM', 'ROA', 'ROE', 'PScore',
                      'CR', 'D/E', 'Revenue', 'YEG', 'YRG', 'EPS', 'BPS', 'DPS'])
        for (company, data) in self.companies.items():
            row = []
            row.append(company)
            row.append(None)
            row.append(None)
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

    def pretty_print_table(self):
        table = prettytable.PrettyTable()
        data = self.convert_to_table()
        table.field_names = data[0]
        for row in data[1:]:
            table.add_row(row)
        print(table)

    def save_to_csv(self):
        data = self.convert_to_table()
        with open('canada.csv', 'w') as output_file:
            csv.writer(output_file).writerows(data)

    def import_data_morningstar(self, ticker):
        data = self.fetch_data(URL_CANADA(ticker))
        current_state = ''
        for row in data:
            if not row:
                continue
            header = row[0]
            if header and not any(row[1:-1]):
                current_state = header
                continue
            ttm_data = _parse_number(row[-1])
            if header == 'Operating Margin':
                self.companies[ticker]['operating_margin'] = ttm_data / 100
            elif header == 'Free Cash Flow/Sales %':
                self.companies[ticker]['free_cash_flow_margin'] = ttm_data / 100
            elif header.startswith('Earnings Per Share '):
                self.companies[ticker]['earnings_per_share'] = ttm_data
            elif header.startswith('Dividends '):
                self.companies[ticker]['dividends_per_share'] = ttm_data
            elif header.startswith('Book Value Per Share * '):
                self.companies[ticker]['book_value_per_share'] = ttm_data
            elif header.startswith('Revenue ') and header.endswith(' Mil'):
                self.companies[ticker]['revenue'] = ttm_data * 1000000
            elif header == 'Return on Assets %':
                self.companies[ticker]['return_on_assets'] = ttm_data / 100
            elif header == 'Return on Equity %':
                self.companies[ticker]['return_on_equity'] = ttm_data / 100
            elif header == 'Current Ratio':
                self.companies[ticker]['current_ratio'] = ttm_data
            elif header == 'Debt/Equity':
                self.companies[ticker]['debt_to_equity_ratio'] = ttm_data
            elif header == '5-Year Average':
                if current_state == 'Revenue %':
                    self.companies[ticker]['revenue_growth_5y'] = _parse_number(row[-2]) / 100
                elif current_state == 'Net Income %':
                    self.companies[ticker]['earnings_growth_5y'] = _parse_number(row[-2]) / 100
            elif header == '3-Year Average':
                if current_state == 'Revenue %':
                    self.companies[ticker]['revenue_growth_3y'] = _parse_number(row[-2]) / 100
                elif current_state == 'Net Income %':
                    self.companies[ticker]['earnings_growth_3y'] = _parse_number(row[-2]) / 100
        self.metrics['ProcessedCompanies'] += 1

    def import_data(self, tickers):
        with shelve.open('screener_cache') as file_cache:
            self.file_cache = file_cache
            for ticker in tickers:
                try:
                    self.import_data_morningstar(ticker)
                except Exception as e:
                    self.metrics['FailedToProcessCompany'] += 1
                    raise e
                    print('Failed to process company %s: %s' % (ticker, e))
        self.pretty_print_table()
        self.save_to_csv()
        print('Metrics: %s' % dict(self.metrics))


if __name__ == '__main__':
    company_list = ['AAV', 'ARE', 'AEM', 'AC', 'ASR', 'AGI', 'AD', 'AQN', 'ATD.B', 'AP.UN', 'ALA', 'AIF', 'APHA', 'ARX', 'AX.UN', 'ACO.X', 'ATA', 'ACB', 'BTO', 'BAD', 'BMO', 'BNS', 'ABX', 'BHC', 'BTE', 'BCE', 'BIR', 'BB', 'BEI.UN', 'BBD.B', 'BLX', 'BYD.UN', 'BAM.A', 'BBU.UN', 'BIP.UN', 'BPY.UN', 'BEP.UN', 'DOO', 'CAE', 'CCO', 'GOOS', 'CAR.UN', 'CM', 'CNR', 'CNQ', 'CP', 'CTC.A', 'CU', 'CWB', 'CFP', 'WEED', 'CPX', 'CAS', 'CCL.B', 'CLS', 'CVE', 'CG', 'CEU', 'GIB.A', 'CSH.UN', 'CHE.UN', 'CHP.UN', 'CHR', 'CIX', 'CGX', 'CCA', 'CIGI', 'CUF.UN', 'CMG', 'CSU', 'BCB', 'CPG', 'CRR.UN', 'DSG', 'DGC', 'DOL', 'DII.B', 'DRG.UN', 'D.UN', 'ECN', 'ELD', 'EFN', 'EMA', 'EMP.A', 'ENB', 'ECA', 'EDV', 'EFX', 'ERF', 'ENGH', 'ESI', 'EIF', 'EXE', 'FFH', 'FTT', 'FCR', 'FR', 'FM', 'FSV', 'FTS', 'FVI', 'FNV', 'FRU', 'MIC', 'WN', 'GEI', 'GIL', 'G', 'GTE', 'GRT.UN', 'GC', 'GWO', 'GUY', 'HR.UN', 'HCG', 'HBM', 'HBC', 'HSE', 'H', 'IMG', 'IGM', 'IMO', 'IAG', 'INE', 'IFC', 'IPL', 'IFP', 'ITP', 'IIP.UN', 'IVN', 'KEL', 'KEY', 'KMP.UN', 'KXS', 'KML', 'K', 'KL', 'GUD', 'LIF', 'LB', 'LNR', 'L', 'LUC', 'LUN', 'MAG', 'MG', 'MFC', 'MFI', 'MRE', 'MAXR', 'MEG', 'MX', 'MRU', 'MNW', 'MSI', 'MTY', 'MTL', 'NA', 'NSU', 'NFI', 'NGD', 'NXE', 'OSB', 'NPI', 'NVU.UN', 'NG', 'NTR', 'NVA', 'OGC', 'ONEX', 'OTEX', 'OR', 'PAAS', 'POU', 'PXT', 'PKI', 'PSI', 'PPL', 'PEY', 'POW', 'PWF', 'PSK', 'PD', 'PBH', 'PVG', 'QBR.B', 'QSR', 'RCH', 'REI.UN', 'RBA', 'RCI.B', 'RY', 'RUS', 'SSL', 'SAP', 'SES', 'SMF', 'VII', 'SJR.B', 'SCL', 'SHOP', 'SIA', 'SW', 'ZZZ', 'SRU.UN', 'SNC', 'TOY', 'SSRM', 'STN', 'SJ', 'SLF', 'SU', 'SPB', 'THO', 'TVE', 'TECK.B', 'T', 'TFII', 'NWC', 'TSGI', 'TRI', 'X', 'TOG', 'TXG', 'TIH', 'TD', 'TOU', 'TA', 'RNW', 'TRP', 'TCL.A', 'TCW', 'TCN', 'TRQ', 'UNS', 'VET', 'WCN', 'WFT', 'WEF', 'WJA', 'WTE', 'WPM', 'WCP', 'WPK', 'WSP', 'YRI']
    Screener().import_data(company_list)
