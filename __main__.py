from tabulate import tabulate
import re
import draft_kings
import pickem
import espn_bet
import odds_shark
import util

#  todo see if we can just exclude if its false and there's no file saved
FETCH_PICKEM = True
FETCH_DRAFKKINGS = True
FETCH_ESPNBET = False
FETCH_ODDSHARK = True

AVG_ALL = 'AVG_ALL' # Doesn't include Odds Shark as of writing
DRAFTKINGS_DIFF_HEADER = 'DK Diff'
DRAFTKINGS_ODDS_HEADER = 'DK Odds'
ESPNBET_DIFF_HEADER = 'ESPN Diff'
ESPNBET_ODDS_HEADER = 'ESPN Odds'
ODDSSHARK_DIFF_HEADER = 'OS Diff'
ODDSSHARK_ODDS_HEADER = 'OS Odds'

SORT_BY_HEADERS = [ODDSSHARK_DIFF_HEADER, ODDSSHARK_ODDS_HEADER] # [Spread Diff Header, Odds Header]

def main():
    pickem_lines = pickem.get_pickem_lines(FETCH_PICKEM)
    os_lines = odds_shark.get_odds_shark_spreads(FETCH_ODDSHARK)
    dk_lines = draft_kings.get_draft_kings_lines(FETCH_DRAFKKINGS)
    espn_lines = espn_bet.get_espn_bet_lines(FETCH_ESPNBET)
    print(build_table(pickem_lines, dk_lines, espn_lines, os_lines))

def build_table(pickem_lines, dk_lines, espn_lines, os_lines):
    final_table = []
    for line in pickem_lines:
        dk_team = get_team_from_map(line['team'], 'd')
        dk_record = get_record(dk_team, dk_lines)
        if dk_record is not None:
            dk_spread_diff = get_spread_diff(line['spread'], dk_record['spread'])
            dk_record['diff'] = dk_spread_diff
        else:
            dk_spread_diff = 0
            dk_record = {'spread': '999', 'odds': '-110', 'diff': '0'}

        espn_team = get_team_from_map(line['team'], 'e', 'd') # Names are the same as Draft Kings
        espn_record = get_record(espn_team, espn_lines)
        if espn_record is not None:
            espn_spread_diff = get_spread_diff(line['spread'], espn_record['spread'])
            espn_record['diff'] = espn_spread_diff
        else:
            espn_spread_diff = 0
            espn_record = {'spread': '999', 'odds': '-110', 'diff': '0'}

        os_team = get_team_from_map(line['team'], 'o')
        os_record = get_record(os_team, os_lines)
        if os_record is not None:
            os_spread_diff = get_spread_diff(line['spread'], os_record['spread'])
            os_record['diff'] = os_spread_diff
        else:
            os_spread_diff = 0
            os_record = {'spread': '999', 'odds': '-110', 'diff': '0'}

        final_table.append({
            'Team': dk_team,
            'PickEm': line['spread'],
            'Odds Shark': f'{os_record["spread"]}{get_spread_display_arrow(os_spread_diff)}',
            ODDSSHARK_ODDS_HEADER: f'{os_record["odds"]}{get_odds_display_arrow(os_record["odds"])}',
            ODDSSHARK_DIFF_HEADER: os_record['diff'],
            'Draft Kings': f'{dk_record["spread"]}{get_spread_display_arrow(dk_spread_diff)}',
            DRAFTKINGS_ODDS_HEADER: f'{dk_record["odds"]}{get_odds_display_arrow(dk_record["odds"])}',
            DRAFTKINGS_DIFF_HEADER: dk_record['diff'],
            'ESPN Bet': f'{espn_record["spread"]}{get_spread_display_arrow(espn_spread_diff)}',
            ESPNBET_ODDS_HEADER: f'{espn_record["odds"]}{get_odds_display_arrow(espn_record["odds"])}',
            ESPNBET_DIFF_HEADER: espn_record['diff']
        })

    # Todo averaging logic is hardcoded here
    # Todo If the spread diffs aren't the same this just sorts by odds of the highest diff
    if SORT_BY_HEADERS[0] == AVG_ALL:
        spread_diff_average = lambda x: ((get_diff_from_table(x, DRAFTKINGS_DIFF_HEADER) + get_diff_from_table(x, ESPNBET_DIFF_HEADER)) / 2)
        odds_average = lambda x: determine_odds_average(x)
        sort_lambda = lambda x: (-spread_diff_average(x), odds_average(x))
    else:
        sort_lambda = lambda x: (-get_diff_from_table(x, SORT_BY_HEADERS[0]), get_odds_from_table(x, SORT_BY_HEADERS[1]))
    sorted_final_table = sorted(final_table, key=sort_lambda)
    table = tabulate(sorted_final_table, headers="keys", tablefmt="fancy_outline")
    return table

def get_diff_from_table(table, spread_header):
    return float(table[spread_header])

def get_odds_from_table(table, odds_header):
    return util.get_odds_float(table[odds_header])

def determine_odds_average(x):
    if get_diff_from_table(x, DRAFTKINGS_DIFF_HEADER) == get_diff_from_table(x, ESPNBET_DIFF_HEADER):
        return (util.american_to_decimal(get_odds_from_table(x, DRAFTKINGS_ODDS_HEADER)) + util.american_to_decimal(get_odds_from_table(x, ESPNBET_ODDS_HEADER))) / 2
    elif get_diff_from_table(x, DRAFTKINGS_DIFF_HEADER) > get_diff_from_table(x, ESPNBET_DIFF_HEADER):
        return util.american_to_decimal(get_odds_from_table(x, DRAFTKINGS_ODDS_HEADER))
    else:
        return util.american_to_decimal(get_odds_from_table(x, ESPNBET_ODDS_HEADER))

name_map = [
    {
        'p': 'Dolphins',
        'd': 'MIA Dolphins',
        'o': 'MIA'
    },
    {
        'p': 'Bills',
        'd': 'BUF Bills',
        'o': 'BUF'
    },
    {
        'p': 'Falcons',
        'd': 'ATL Falcons',
        'o': 'ATL'
    },
    {
        'p': 'Panthers',
        'd': 'CAR Panthers',
        'o': 'CAR'
    },
    {
        'p': 'Packers',
        'd': 'GB Packers',
        'o': 'GB'
    },
    {
        'p': 'Browns',
        'd': 'CLE Browns',
        'o': 'CLE'
    },
    {
        'p': 'Texans',
        'd': 'HOU Texans',
        'o': 'HOU'
    },
    {
        'p': 'Jaguars',
        'd': 'JAX Jaguars',
        'o': 'JAC'
    },
    {
        'p': 'Bengals',
        'd': 'CIN Bengals',
        'o': 'CIN'
    },
    {
        'p': 'Vikings',
        'd': 'MIN Vikings',
        'o': 'MIN'
    },
    {
        'p': 'Steelers',
        'd': 'PIT Steelers',
        'o': 'PIT'
    },
    {
        'p': 'Patriots',
        'd': 'NE Patriots',
        'o': 'NE'
    },
    {
        'p': 'Rams',
        'd': 'LA Rams',
        'o': 'LAR'
    },
    {
        'p': 'Eagles',
        'd': 'PHI Eagles',
        'o': 'PHI'
    },
    {
        'p': 'Jets',
        'd': 'NY Jets',
        'o': 'NYJ'
    },
    {
        'p': 'Buccaneers',
        'd': 'TB Buccaneers',
        'o': 'TB'
    },
    {
        'p': 'Colts',
        'd': 'IND Colts',
        'o': 'IND'
    },
    {
        'p': 'Titans',
        'd': 'TEN Titans',
        'o': 'TEN'
    },
    {
        'p': 'Raiders',
        'd': 'LV Raiders',
        'o': 'LV'
    },
    {
        'p': 'Commanders',
        'd': 'WAS Commanders',
        'o': 'WAS',
        'e': 'WSH Commanders'
    },
    {
        'p': 'Broncos',
        'd': 'DEN Broncos',
        'o': 'DEN'
    },
    {
        'p': 'Chargers',
        'd': 'LA Chargers',
        'o': 'LAC'
    },
    {
        'p': 'Saints',
        'd': 'NO Saints',
        'o': 'NO'
    },
    {
        'p': 'Seahawks',
        'd': 'SEA Seahawks',
        'o': 'SEA'
    },
    {
        'p': 'Cowboys',
        'd': 'DAL Cowboys',
        'o': 'DAL'
    },
    {
        'p': 'Bears',
        'd': 'CHI Bears',
        'o': 'CHI'
    },
    {
        'p': 'Cardinals',
        'd': 'ARI Cardinals',
        'o': 'ARI'
    },
    {
        'p': '49ers',
        'd': 'SF 49ers',
        'o': 'SF'
    },
    {
        'p': 'Chiefs',
        'd': 'KC Chiefs',
        'o': 'KC'
    },
    {
        'p': 'Giants',
        'd': 'NY Giants',
        'o': 'NYG'
    },
    {
        'p': 'Lions',
        'd': 'DET Lions',
        'o': 'DET'
    },
    {
        'p': 'Ravens',
        'd': 'BAL Ravens',
        'o': 'BAL'
    }
]

def get_team_from_map(pickemTeam, key, backup_key=None):
    for item in name_map:
        if item['p'] == pickemTeam:
            if item.get(key) is not None: return item[key]
            elif (backup_key is not None) and item.get(backup_key) is not None: return item[backup_key]
    return None

def get_record(team, data):
    for item in data:
        if item['team'] == team:
            return item
    return None

def get_spread_diff(pickemSpread, dkSpread):
    #  Edit: there are ties in regular season
    # offset = 0
    # pickemSpread = float(pickemSpread)
    # dkSpread = float(dkSpread)
    # if (pickemSpread < 0 and pickemSpread > -1 and dkSpread > pickemSpread) or (dkSpread > 0 and dkSpread < 1 and pickemSpread < dkSpread):
    #     offset = 1
    # elif (pickemSpread > 0 and pickemSpread < 1 and dkSpread < pickemSpread) or (dkSpread < 0 and dkSpread > -1 and pickemSpread > dkSpread):
    #     offset = -1

    # return str(pickemSpread - dkSpread + offset) + ('*' if offset != 0 else '')
    return float(pickemSpread) - float(dkSpread)

def get_spread_display_arrow(spread_diff):
    if isinstance(spread_diff, str):
        spread_diff = float(re.sub(r'[^\d.-]', '',spread_diff))
    display_arrow = ''
    if spread_diff >= 1:
        display_arrow = '\033[92m \u2B9D\033[00m'
    elif spread_diff >=0.5 and spread_diff < 1:
        display_arrow = ' \u2B9D'
    elif spread_diff > 0 and spread_diff < 0.5:
        display_arrow = ' ^'
    if spread_diff <= -1:
        display_arrow = '\033[91m \u2B9F\033[00m'
    elif spread_diff <= -0.5 and spread_diff > -1:
        display_arrow = ' \u2B9f'
    elif spread_diff < 0 and spread_diff > -0.5:
        display_arrow = ' v'

    return display_arrow

def get_odds_display_arrow(odds):
    display_arrow = ''
    if (str(odds).lower() == 'even'):
        odds = 100
    if float(odds) <= -120:
        display_arrow = '\033[92m \u2B9D\033[00m'
    elif float(odds) <= -115:
        display_arrow = ' \u2B9D'
    elif float(odds) < -110: # Book default
        display_arrow = ' ^'
    elif float(odds) >= -100: # Even
        display_arrow = '\033[91m \u2B9F\033[00m'
    elif float(odds) >= -105:
        display_arrow = ' \u2B9f'
    elif float(odds) > -110:
        display_arrow = ' v'

    return display_arrow


if __name__ == '__main__':
    main()