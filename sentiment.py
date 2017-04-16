import urllib
import urllib.request
import urllib.parse
import json

with open("hodkey") as f:
    key = f.read()

def analyze(text):
    #curl "https://api.havenondemand.com/1/api/sync/analyzesentiment/v2?text=It+was+fucking+amazing&language=eng&apikey=33058db7-e5a3-4dbd-8528-ff126747b673"

    q = {"language":"eng", "apikey":key}
    qs = urllib.parse.urlencode(q)
    url = ["https",
           'api.havenondemand.com',
           '/1/api/sync/analyzesentiment/v2',
           "",
           qs,
           ""]
    url = urllib.parse.urlunparse(url)

    if type(text) == str:
        url += "&text=" 
        url += urllib.parse.quote(text)
    else:
        for t in text:
            url += "&text="
            url += urllib.parse.quote(t)
    
    req = urllib.request.Request(url)
    
    resp = urllib.request.urlopen(req)

    data = resp.read()

    text = data.decode("utf-8")

    obj = json.loads(text)

    return obj["sentiment_analysis"]

if __name__ == "__main__":
    res = analyze(["it was shit", "it was great"])
    print(json.dumps(res, indent=True))