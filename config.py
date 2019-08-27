MARKETS = [
    {
        'output_file': 'canada.csv',
        'currency': 'CAD',
        'company_list': [
            'AAV', 'ARE', 'AEM', 'AC', 'ASR', 'AGI', 'AD', 'AQN', 'ATD.B', 'AP.UN',
            'ALA', 'AIF', 'APHA', 'ARX', 'AX.UN', 'ACO.X', 'ATA', 'ACB', 'BTO', 'BAD',
            'BMO', 'BNS', 'ABX', 'BHC', 'BTE', 'BCE', 'BIR', 'BB', 'BEI.UN', 'BBD.B',
            'BLX', 'BYD.UN', 'BAM.A', 'BBU.UN', 'BIP.UN', 'BPY.UN', 'BEP.UN', 'DOO', 'CAE', 'CCO',
            'GOOS', 'CAR.UN', 'CM', 'CNR', 'CNQ', 'CP', 'CTC.A', 'CU', 'CWB', 'CFP',
            'WEED', 'CPX', 'CAS', 'CCL.B', 'CLS', 'CVE', 'CG', 'CEU', 'GIB.A', 'CSH.UN',
            'CHE.UN', 'CHP.UN', 'CHR', 'CIX', 'CGX', 'CCA', 'CIGI', 'CUF.UN', 'CMG', 'CSU',
            'BCB', 'CPG', 'CRR.UN', 'DSG', 'DGC', 'DOL', 'DII.B', 'DRG.UN', 'D.UN', 'ECN',
            'ELD', 'EFN', 'EMA', 'EMP.A', 'ENB', 'ECA', 'EDV', 'EFX', 'ERF', 'ENGH',
            'ESI', 'EIF', 'EXE', 'FFH', 'FTT', 'FCR', 'FR', 'FM', 'FSV', 'FTS',
            'FVI', 'FNV', 'FRU', 'MIC', 'WN', 'GEI', 'GIL', 'G', 'GTE', 'GRT.UN',
            'GC', 'GWO', 'GUY', 'HR.UN', 'HCG', 'HBM', 'HBC', 'HSE', 'H', 'IMG',
            'IGM', 'IMO', 'IAG', 'INE', 'IFC', 'IPL', 'IFP', 'ITP', 'IIP.UN', 'IVN',
            'KEL', 'KEY', 'KMP.UN', 'KXS', 'KML', 'K', 'KL', 'GUD', 'LIF', 'LB',
            'LNR', 'L', 'LUC', 'LUN', 'MAG', 'MG', 'MFC', 'MFI', 'MRE', 'MAXR',
            'MEG', 'MX', 'MRU', 'MSI', 'MTY', 'MTL', 'NA', 'NFI', 'NGD',
            'NXE', 'OSB', 'NPI', 'NVU.UN', 'NG', 'NTR', 'NVA', 'OGC', 'ONEX', 'OTEX',
            'OR', 'PAAS', 'POU', 'PXT', 'PKI', 'PSI', 'PPL', 'PEY', 'POW', 'PWF',
            'PSK', 'PD', 'PBH', 'PVG', 'QBR.B', 'QSR', 'RCH', 'REI.UN', 'RBA', 'RCI.B',
            'RY', 'RUS', 'SSL', 'SAP', 'SES', 'SMF', 'VII', 'SJR.B', 'SCL', 'SHOP',
            'SIA', 'SW', 'ZZZ', 'SRU.UN', 'SNC', 'TOY', 'SSRM', 'STN', 'SJ', 'SLF',
            'SU', 'SPB', 'TVE', 'TECK.B', 'T', 'TFII', 'NWC', 'TSGI', 'TRI',
            'X', 'TOG', 'TXG', 'TIH', 'TD', 'TOU', 'TA', 'RNW', 'TRP', 'TCL.A',
            'TCW', 'TCN', 'TRQ', 'UNS', 'VET', 'WCN', 'WFT', 'WEF', 'WJA', 'WTE',
            'WPM', 'WCP', 'WPK', 'WSP', 'YRI'
        ],
        'url_template': lambda ticker: 'http://financials.morningstar.com/ajax/exportKR2CSV.html?t=%s&culture=en-CA&region=CAN' % ticker,
        'profile_url_template': lambda ticker: 'https://finance.yahoo.com/quote/%s.TO/profile' % ticker.replace('.', '-'),
        'share_count': {
            'url_template': lambda ticker: 'https://finance.yahoo.com/quote/%s.TO/key-statistics' % ticker.replace('.', '-'),
            'selector': '#Col1-3-KeyStatistics-Proxy > section > div.Mstart\\28 a\\29.Mend\\28 a\\29 > div.Fl\\28 end\\29.W\\28 50\\25 \\29.smartphone_W\\28 100\\25 \\29 > div > div:nth-child(2) table > tbody > tr:nth-child(3) > td:nth-child(2)'
        }
    }
]
