from tabulate import tabulate
import re
import draft_kings
import pickem
import espn_bet

FETCH_PICKEM = False
FETCH_DRAFKKINGS = False
FETCH_ESPNBET = False

DRAFTKINGS_ODDS_HEADER = 'DK Odds'
DRAFTKINGS_DIFF_HEADER = 'DK Diff'
ESPNBET_ODDS_HEADER = 'ESPN Odds'
ESPNBET_DIFF_HEADER = 'ESPN Diff'

SORT_BY_HEADERS = [DRAFTKINGS_DIFF_HEADER, DRAFTKINGS_ODDS_HEADER] # [Spread Diff Header, Odds Header]

def main():
    pickem_lines = pickem.get_pickem_lines(FETCH_PICKEM)
    dk_lines = draft_kings.get_draft_kings_lines(FETCH_DRAFKKINGS)
    espn_lines = espn_bet.get_espn_bet_lines(FETCH_ESPNBET)
    print(build_table(pickem_lines, dk_lines, espn_lines))

def build_table(pickem_lines, dk_lines, espn_lines):
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

        final_table.append({
            'Team': dk_team,
            'PickEm': line['spread'],
            'Draft Kings': f'{dk_record["spread"]}{get_spread_display_arrow(dk_spread_diff)}',
            DRAFTKINGS_ODDS_HEADER: f'{dk_record["odds"]}{get_odds_display_arrow(dk_record["odds"])}',
            DRAFTKINGS_DIFF_HEADER: dk_record['diff'],
            'ESPN Bet': f'{espn_record["spread"]}{get_spread_display_arrow(espn_spread_diff)}',
            ESPNBET_ODDS_HEADER: f'{espn_record["odds"]}{get_odds_display_arrow(espn_record["odds"])}',
            ESPNBET_DIFF_HEADER: espn_record['diff']
        })

    sorted_final_table = sorted(final_table, key=lambda x: (-float(x[SORT_BY_HEADERS[0]]), float(re.sub(r'[^\d.-]', '', re.sub(r'Even', '0', x[SORT_BY_HEADERS[1]], flags=re.IGNORECASE)))))
    table = tabulate(sorted_final_table, headers="keys", tablefmt="fancy_outline")
    return table

name_map = [
    {
        'p': 'Dolphins',
        'd': 'MIA Dolphins'
    },
    {
        'p': 'Bills',
        'd': 'BUF Bills'
    },
    {
        'p': 'Falcons',
        'd': 'ATL Falcons'
    },
    {
        'p': 'Panthers',
        'd': 'CAR Panthers'
    },
    {
        'p': 'Packers',
        'd': 'GB Packers'
    },
    {
        'p': 'Browns',
        'd': 'CLE Browns'
    },
    {
        'p': 'Texans',
        'd': 'HOU Texans'
    },
    {
        'p': 'Jaguars',
        'd': 'JAX Jaguars'
    },
    {
        'p': 'Bengals',
        'd': 'CIN Bengals'
    },
    {
        'p': 'Vikings',
        'd': 'MIN Vikings'
    },
    {
        'p': 'Steelers',
        'd': 'PIT Steelers'
    },
    {
        'p': 'Patriots',
        'd': 'NE Patriots'
    },
    {
        'p': 'Rams',
        'd': 'LA Rams'
    },
    {
        'p': 'Eagles',
        'd': 'PHI Eagles'
    },
    {
        'p': 'Jets',
        'd': 'NY Jets'
    },
    {
        'p': 'Buccaneers',
        'd': 'TB Buccaneers'
    },
    {
        'p': 'Colts',
        'd': 'IND Colts'
    },
    {
        'p': 'Titans',
        'd': 'TEN Titans'
    },
    {
        'p': 'Raiders',
        'd': 'LV Raiders'
    },
    {
        'p': 'Commanders',
        'd': 'WAS Commanders',
        'e': 'WSH Commanders'
    },
    {
        'p': 'Broncos',
        'd': 'DEN Broncos'
    },
    {
        'p': 'Chargers',
        'd': 'LA Chargers'
    },
    {
        'p': 'Saints',
        'd': 'NO Saints'
    },
    {
        'p': 'Seahawks',
        'd': 'SEA Seahawks'
    },
    {
        'p': 'Cowboys',
        'd': 'DAL Cowboys'
    },
    {
        'p': 'Bears',
        'd': 'CHI Bears'
    },
    {
        'p': 'Cardinals',
        'd': 'ARI Cardinals'
    },
    {
        'p': '49ers',
        'd': 'SF 49ers'
    },
    {
        'p': 'Chiefs',
        'd': 'KC Chiefs'
    },
    {
        'p': 'Giants',
        'd': 'NY Giants'
    },
    {
        'p': 'Lions',
        'd': 'DET Lions'
    },
    {
        'p': 'Ravens',
        'd': 'BAL Ravens'
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
    elif spread_diff > 0 and spread_diff < 1:
        display_arrow = ' \u2B9D'
    if spread_diff <= -1:
        display_arrow = '\033[91m \u2B9F\033[00m'
    elif spread_diff < 0 and spread_diff > -1:
        display_arrow = ' \u2B9f'

    return display_arrow

def get_odds_display_arrow(odds):
    display_arrow = ''
    if (odds.lower() == 'even'):
        odds = 0
    if float(odds) <= -120:
        display_arrow = '\033[92m \u2B9D\033[00m'
    elif float(odds) <= -115:
        display_arrow = ' \u2B9D'
    elif float(odds) < -110:
        display_arrow = ' ^'
    elif float(odds) >= 0:
        display_arrow = '\033[91m \u2B9F\033[00m'
    elif float(odds) > -105:
        display_arrow = ' \u2B9f'
    elif float(odds) > -110:
        display_arrow = ' v'

    return display_arrow


if __name__ == '__main__':
    main()