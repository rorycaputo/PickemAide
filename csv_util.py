import csv

def create_csv(tabulate_dict, out_name):
    headers = []
    for event in tabulate_dict:
        for key in event:
            if key not in headers:
                headers.append(key)

    with open(out_name, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(tabulate_dict)

    return out_name