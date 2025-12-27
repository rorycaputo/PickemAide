from lxml import html
# import html as phtml
from datetime import datetime, timedelta
import apis
import util
import statistics
import math

OUTPUT_FILE = 'resources/odds_shark.html'

EXCLUDED_BOOKS = [
    # 'CAESARS',
    # 'BRACCO',
    # 'FANDUEL',
    # 'BETMGM',
    'DRAFTKINGS'
    ]

# spread_url = f'https://www.oddsshark.com/api/ticker/nfl?_format=json' (API call that didn't have all the data)
spread_url = 'https://www.oddsshark.com/nfl/odds'

def get_spread_html(fetch=True):
    if fetch:
        headers = {
            'Host': 'www.oddsshark.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'DNT': '1',
            'Alt-Used': 'www.oddsshark.com',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'cross-site',
            'Priority': 'u=0, i',
            'TE': 'trailers'
        }

        # params = {
        #     '_format': 'json',
        # }

        body = apis.call_get_api(spread_url, headers)
        if body is not None:
            odds_shark_html = body.text
            print(f'Writing Odds Shark html to {OUTPUT_FILE} for later use')
            util.write_string_to_file(odds_shark_html, OUTPUT_FILE)
            return html.fromstring(odds_shark_html)
        return None
    else:
        with open(OUTPUT_FILE) as file:
            return html.fromstring(file.read())

# Output format: {'team': 'MIA', 'spread': '12.5', 'odds': '-110', 'diff': ''}
# spread is the average of all non-excluded spreads
# odds is the average of all odds values from the mode of the non-excluded spreads
def get_odds_shark_spreads(fetch=True):
    odds_shark_html = get_spread_html(fetch)
    current_date = datetime.now()
    tuesday = current_date + timedelta(days=(1 - current_date.weekday()) % 7)

    os_spreads_data = []
    # Generates all_events = [{team: '', spreads: [{spread: '', odds: '', book: ''}]}]
    all_events = []
    for event in odds_shark_html.xpath("//div[starts-with(@class, 'odds--group__event-container football')]"):
        event_date = datetime.fromtimestamp(int(event.get("data-event-date")))
        if current_date <= event_date <= tuesday:
            events_row = []
            for participant_name in event.xpath('.//div[@class="participant-name"]//span[@class="mobile-only-name"]'):
                events_row.append({'team': participant_name.text, 'spreads': [], 'average_spread': None, 'average_mode_odds': None})
            opening_or_best_or_none_xpath = "boolean(.//div[@class='mobile-only-best-odds' or @class='odds-spread opening' or @class='odds-type-no-odds'])"
            for first_row in event.xpath(".//div[@class='first-row']"):
                if not first_row.xpath(opening_or_best_or_none_xpath):
                    spread = get_spreads_from_cell(first_row, EXCLUDED_BOOKS)
                    if spread is not None:
                        events_row[0]['spreads'].append(spread)
            for second_row in event.xpath(".//div[@class='second-row']"):
                if not second_row.xpath(opening_or_best_or_none_xpath):
                    spread = get_spreads_from_cell(second_row, EXCLUDED_BOOKS)
                    if spread is not None:
                        events_row[1]['spreads'].append(spread)
            for side in events_row:
                all_events.append(side)

    for event in all_events:
        event_spreads = event['spreads']
        mode_odds_list = get_odds_with_spread(event_spreads, get_spread_mode(event_spreads))
        os_spreads_data.append({
            'team': event['team'],
            'spread': round(get_average_spread(event_spreads), 3),
            'odds': round(util.determine_odds_average(mode_odds_list), 3),
            'diff': ''
        })
    
    return os_spreads_data
            
def get_spreads_from_cell(spread_cell, excluded_books=[]):
    spread = spread_cell.xpath('.//div[@data-odds-spread]/text()')[0].strip()
    odds = spread_cell.xpath('.//div[@data-odds-signed-spread]/text()')[0].strip()
    book = spread_cell.xpath('.//a[@class="odds-data-cell"]/text()')[0].strip()

    if book in excluded_books:
        return None
    return {'spread': spread, 'odds': odds, 'book': book}

def get_average_spread(spreads):
    spread_values = [float(item['spread']) for item in spreads if 'spread' in item]
    if spread_values:
        average = sum(spread_values) / len(spread_values)
        return average
    else:
        return None

def get_spread_mode(spreads):
    spread_values = [float(item['spread']) for item in spreads if 'spread' in item]
    if spread_values:
        mode = statistics.mode(spread_values)
        return mode
    else:
        return None

def get_odds_with_spread(spreads, spread_value):
    odds_with_spread = []
    for spread in spreads:
        if math.isclose(float(spread['spread']), float(spread_value), abs_tol=0.01):
            odds_with_spread.append(spread['odds'])
    return odds_with_spread