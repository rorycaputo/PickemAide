import selenium_pa
from lxml import html
import re
import util

OUTPUT_FILE = 'resources/pickem.html'
# pickem_html_url = 'https://picks.cbssports.com/football/pickem/pools/kbxw63b2geztqnjuha2ds===?entryId=ivxhi4tzhizdcnbrgm2tinbs'

u = 'caputo.rory@gmail.com'
p = 'Base 64 Encoded'

# Output format: {'team': 'Dolphins', 'spread': '+12.5'}
def get_pickem_lines(fetch=True):
    if fetch:
        pickem_html = selenium_pa.get_pickem_html(u,p)
        if pickem_html is not None:
            pickem_html = html.fromstring(pickem_html)
            for script in pickem_html.xpath('//script'):
                script.getparent().remove(script)
            for style in pickem_html.xpath('//style'):
                style.getparent().remove(style)
            print(f'Writing PickEm html to {OUTPUT_FILE} for later use')
            util.write_string_to_file(html.tostring(pickem_html, encoding='unicode'), OUTPUT_FILE)
    else:
        with open(OUTPUT_FILE) as file:
            pickem_html = html.fromstring(file.read())

    results = []
    for h3 in pickem_html.xpath('//h3'):
        # HTML classes might be mui-style-2wey69 and mui-style-o041sw if you want to use those instead
        fifth_parent = str(html.tostring(h3.xpath('ancestor::*[position()=5]')[0]))
        if 'final' not in fifth_parent and not re.match(r'.*:\d\d<.*', fifth_parent):
            name = h3.text.strip()
            spread = h3.xpath('parent::div/following-sibling::div//div[@data-cy="spread"]/span')[0].text.strip()
            results.append({'team': name, 'spread': spread})

    return results

def has_no_children_with_text(element, text):
    if element is None:
        return True
    if element.text == text:
        return False
    for child in element:
        if has_no_children_with_text(child, text):
            continue
        if child.text == text:
            return False
    return True