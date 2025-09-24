from lxml import html
import json
from datetime import datetime, timedelta
import apis
import util

OUTPUT_FILE = 'resources\DK_markets_resp.json'

# lines_url = f'https://sportsbook.draftkings.com/leagues/football/nfl'
lines_url = 'https://sportsbook-nash.draftkings.com/sites/US-IL-SB/api/sportscontent/controldata/league/leagueSubcategory/v1/markets?isBatchable=false&templateVars=88808%2C4518&eventsQuery=%24filter%3DleagueId%20eq%20%2788808%27%20AND%20clientMetadata%2FSubcategories%2Fany%28s%3A%20s%2FId%20eq%20%274518%27%29&marketsQuery=%24filter%3DclientMetadata%2FsubCategoryId%20eq%20%274518%27%20AND%20tags%2Fall%28t%3A%20t%20ne%20%27SportcastBetBuilder%27%29&include=Events&entity=events'

def get_lines_json(fetch=True):
    if fetch:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Referer': 'https://sportsbook.draftkings.com/',
            'Content-Type': 'application/json charset=utf-8',
            'X-Client-Feature': 'leagueSubcategory',
            'X-Client-Name': 'web',
            'X-Client-Page': 'league',
            'X-Client-Version': '2537.2.1.7',
            'X-Client-Widget-Name': 'cms',
            'X-Client-Widget-Version': '1.3.9',
            'Origin': 'https://sportsbook.draftkings.com',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'Priority': 'u=4',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'TE': 'trailers'
        }
        # params = {
        #     'isBatchable': 'false',
        #     'templateVars': '88808%2C4518',
        #     'eventsQuery': '%24filter%3DleagueId%20eq%20%2788808%27%20AND%20clientMetadata%2FSubcategories%2Fany%28s%3A%20s%2FId%20eq%20%274518%27%29',
        #     'marketsQuery': '%24filter%3DclientMetadata%2FsubCategoryId%20eq%20%274518%27%20AND%20tags%2Fall%28t%3A%20t%20ne%20%27SportcastBetBuilder%27%29',
        #     'include': 'Events',
        #     'entity': 'events'
        # }
        body = apis.call_get_api(lines_url, headers, None)
        if body is not None:
            print(f'Writing Draft Kings json to {OUTPUT_FILE} for later use')
            util.write_string_to_file(body, OUTPUT_FILE)
        return body.json()
    else:
        with open('resources\DK_markets_resp.json') as file:
            data = json.load(file)
        return data

# Output format: {'team': 'MIA Dolphin', 'spread': '12.5', 'odds': '-110', 'diff': ''}
def get_draft_kings_lines(fetch=True):
    current_date = datetime.now()
    lines_json = get_lines_json(fetch)

    week_marketIds = []
    dk_lines_data = []
    for event in lines_json['events']:
        start_event_date = datetime.strptime(event['startEventDate'][:-9], '%Y-%m-%dT%H:%M:%S')
        if start_event_date <= current_date + timedelta(days=7):
            event_id = event['id']
            for market in lines_json['markets']:
                market_id = market['id']
                if market['name'] == 'Spread' and market['eventId'] == event_id:
                    week_marketIds.append(market_id)
    for selection in lines_json['selections']:
        if selection['marketId'] in week_marketIds:
            label = selection['label']
            points = selection.get('points')
            displayOdds_american = selection['displayOdds'].get('american').replace('−', '-')
            # print(f"Label: {label}, Points: {points}, Display Odds (American): {displayOdds_american}")
            dk_lines_data.append({
                'team': label,
                'spread': points,
                'odds': displayOdds_american,
                'diff': ''
            })

    return dk_lines_data