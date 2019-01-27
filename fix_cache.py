#!/usr/bin/env python
import collections
import config
import random
import shelve
import time
import traceback


def copy_or_fix_entry(cache_key, file_cache, file_cache_new, ttl, metrics):
    if cache_key in file_cache:
        entry = file_cache[cache_key]
        if type(file_cache[cache_key]) != dict:
            ttl = random.randint(15, 30) * 86400  # 15-30 days in seconds
            file_cache_new[cache_key] = {'content': entry, 'expiry': time.time() + ttl}
            metrics['AddedExpiryToEntry'] += 1
        else:
            if 'ttl' in entry:
                entry['expiry'] = time.time() + entry['ttl']
                del entry['ttl']
                file_cache_new[cache_key] = entry
                metrics['ConvertedTTLToExpiryInEntry'] += 1
            else:
                file_cache_new[cache_key] = entry
                metrics['CopiedEntry'] += 1


def fix_cache(market, ticker, file_cache, file_cache_new, metrics):
    financials_url = market['url_template'](ticker)
    financials_url_ttl = random.randint(15, 30) * 86400  # 15-30 days in seconds
    copy_or_fix_entry(financials_url, file_cache, file_cache_new, financials_url_ttl, metrics)

    share_count_cache_key = 'share_count__%s' % market['share_count']['url_template'](ticker)
    share_count_ttl = random.randint(15, 30) * 86400  # 15-30 days in seconds
    copy_or_fix_entry(share_count_cache_key, file_cache, file_cache_new, share_count_ttl, metrics)

    sector_cache_key = 'sector__%s' % market['profile_url_template'](ticker)
    sector_ttl = random.randint(150, 300) * 86400  # 150-300 days in seconds
    copy_or_fix_entry(sector_cache_key, file_cache, file_cache_new, sector_ttl, metrics)

    metrics['ProcessedCompanies'] += 1

if __name__ == '__main__':
    with shelve.open('screener_cache') as file_cache, shelve.open('screener_cache_new') as file_cache_new:
        metrics = collections.defaultdict(lambda: 0)
        for market in config.MARKETS:
            assert ('output_file' in market and 'company_list' in market and
                    'url_template' in market and 'profile_url_template' in market and
                    'share_count' in market and 'url_template' in market['share_count'] and
                    'selector' in market['share_count'])
            for ticker in market['company_list']:
                try:
                    fix_cache(market, ticker, file_cache, file_cache_new, metrics)
                except:
                    metrics['FailedToProcessCompany'] += 1
                    print('Failed to process company %s' % ticker)
                    traceback.print_exc()
    print('Metrics: %s' % dict(metrics))
