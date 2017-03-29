import re
import dateutil.parser as dateparser
import datetime
import pendulum
timePat = re.compile(r"\b(([012]?\d:?[012345][05])|([12]?\d(\d[05])?\s*[aApP][mM]))\b")
utctz = pendulum.timezone("UTC")

def findTime(string):
    m = timePat.search(string)
    if m:
        time = m.group(1)
        return time
    return None

def to_utc(string, city):
    tz = pendulum.timezone(city)
    today = datetime.datetime.utcnow().date()
    s0 = str(today)
    d = pendulum.parse(s0 + " " + string, tz = tz)
    dutc = utctz.convert(d)
    
    return dutc.time()

if __name__ == "__main__":
    inputs = ["Let's do numa at 2000 ok?", "Let's do numa at 19:00"]
    for inp in inputs:
        t = findTime(inp)
        if t:
            print(to_utc(t, "Europe/London"))


def offset_from_now(time):
    x = pendulum.utcnow().time()
    if time > x:
        x = x.diff(time)
        hours = x.hours
        minutes = x.minutes
    else:
        x = pendulum.time(23,59,59) - time.diff(x)
        hours = x.hour
        minutes = x.minute
    if hours == 0:
        return "{0}m".format(minutes)
    else:
        return "{0}h{1:02d}m".format(hours, minutes)

if __name__ == "__main__":
    inputs = ["Let's do numa at 2300 ok?", "Let's do numa at 2100 ok?"]
    for inp in inputs:
        t = findTime(inp)
        if t:
            t = to_utc(t, "Europe/London")
            tt = offset_from_now(t)
            print(tt + " from now")
