import json
with open('data.json') as f:
    data = json.load(f)

with open('request.json', 'w') as f:
    json.dump({'text': data[0]['fields']['text']}, f)
