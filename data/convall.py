import json
import requests

with open('data_fixed.json') as f:
    data = json.load(f)

# just the first record
text = data[0]['text']
print(json.dumps(response.json(), indent=2))
