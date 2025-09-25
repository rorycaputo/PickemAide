#  The SHA vlaue for each REST call you get from the chunk script: https://espnbet.com/_next/static/chunks/pages/index-46ad9c586d0dff59.js
#  No cookie needed
# Which oyu can get the filename for via the HTML GET: https://espnbet.com/sport/football/organization/united-states/competition/nfl/section/lines

#  To get bearer token:
# Need to call https://sportsbook-espnbet.us-il.thescore.bet since us defualt one returns error.
# Don't need the cookie on this^
#  token is under `anonymousToken`

#  Then call the operationName=Marketplace api with the auth token
from lxml import html
import json
import re
import apis
import util

OUTPUT_FILE = 'resources/espn_markets_resp.json'

espn_base_url = "https://espnbet.com"
espn_lines_url = f'{espn_base_url}/sport/football/organization/united-states/competition/nfl/section/lines'

def get_espn_html():
    return html.fromstring(apis.call_get_api(espn_lines_url).text)

def get_chunk_url(html):
    script_tags = html.xpath('//script[@src[contains(.,"/_next/static/chunks/pages/index-")]]')
    chunk_path = script_tags[0].attrib.get('src') if script_tags else None

    return f'{espn_base_url}{chunk_path}'

def get_sha_token(chunk_blob, op_name):
    re_exp = f'"{op_name}":"([^"]+)"'
    return re.search(re_exp, chunk_blob).group(1)

def get_bearer_token(startup_resp):
    return startup_resp['data']['startup']['anonymousToken']

def make_api_calls():
    espn_chunk_url = get_chunk_url(get_espn_html())
    espn_chunk = apis.espn_chunk_get(espn_chunk_url)
    startup_sha = get_sha_token(espn_chunk, 'Startup')
    marketplace_sha = get_sha_token(espn_chunk, 'Marketplace')
    bearer_token = get_bearer_token(apis.espn_startup_get(startup_sha))
    # espn_marketplace_json = get_espn_marketplace_json()
    espn_marketplace_resp = apis.espn_marketplace_get(marketplace_sha, bearer_token)
    if espn_marketplace_resp is not None:
        print(f'Writing ESPN Bet json to {OUTPUT_FILE} for later use')
        util.write_string_to_file(espn_marketplace_resp, OUTPUT_FILE)
        return espn_marketplace_resp.json()
    return None

# Output format: {'team': 'MIA Dolphin', 'spread': 12.5, 'odds': '-110', 'diff': ''}
def get_espn_bet_lines(fetch=True):
    if fetch:
        espn_marketplace_json = make_api_calls()
    else:
        with open(OUTPUT_FILE) as file:
            espn_marketplace_json = json.load(file)
    # markets = espn_marketplace_json['data']['page']['defaultChild']['sectionChildren']
    for sectionChild in espn_marketplace_json['data']['page']['defaultChild']['sectionChildren']:
        if sectionChild['__typename'] == 'MarketplaceShelf':
            marketplaceShelfChildren = sectionChild['marketplaceShelfChildren']
    espn_spread_data = []
    for marketplaceShelfChild in marketplaceShelfChildren:
        for market in marketplaceShelfChild['markets']:
            if market['name'] == 'Game Spread':
                for selection in market['selections']:
                    espn_spread_data.append({
                        'team': selection['participant']['mediumName'],
                        'spread': selection['points']['decimalPoints'],
                        'odds': selection['odds']['formattedOdds'],
                        'diff': ''
                    })

    return espn_spread_data
