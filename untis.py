import webuntis, datetime
from typing import Any

from webuntis import errors

from env import loadenv


time_format_date = "%Y-%m-%d"
time_format = "%H%M"


def get_untis_data(raum :str) -> list[Any] | None:
    #load env from docker in class "env"

    #time
    now = datetime.datetime.now()
    start = datetime.datetime.now()

    try:
       env = loadenv()
    except EnvironmentError as e:
        print(f"Environment Error: {e}")
        return

    login = webuntis.Session(
        server=env.server,
        username=env.username,
        password=env.password,
        school=env.school,
        useragent=env.useragent,
    )

    login.login()

    #end of schoolyear
    schuljahr_ende = login.schoolyears().current.end.date()
    end_date = min(now.date() + datetime.timedelta(days=7), schuljahr_ende)
    end = datetime.datetime.combine(end_date, datetime.time.max)

    #sortiert nur nach den raum
    rooms = login.rooms().filter(name=raum)

    timetable = login.timetable(room=rooms[0], start=start,end=end)
    timetable = sorted(timetable, key=lambda x: x.start)
    stunden = []

    for h in timetable:
        #spart Zeit
        #löscht alte Daten
        if h.end.date() < now.date():
            continue
        #löscht alle gelaufene Stunden
        if h.end.date() == now.date() and h.end.time() < now.time():
            continue

        #leere klasse
        try:
            classroom = " ".join([r.name for r in h.rooms])
        except (IndexError, AttributeError):
            classroom = "---"

        #leerer Lehrer
        try:
            teacher = " ".join([t.name for t in h.teachers])
        except (IndexError, AttributeError, errors.RemoteError):
            teacher = "---"


        eintrag = {
            "date":  h.start.strftime(time_format_date),
            "start_time": h.start.strftime(time_format),
            "end_time" : h.end.strftime(time_format),
            "klasse": short_klassen([k.name for k in h.klassen]),
            "teacher": teacher,
            "classroom":  raum_change(classroom, raum),
            "subject": " ".join([s.name for s in h.subjects]),
            "code": h.code if h.code is not None else "",
        }

        if not classroom == raum:
            eintrag["room_changed"] = True

        stunden.append(eintrag)
    login.logout()
    return stunden

def short_klassen(klassen: list[Any]) -> str | Any:
    #wird aus untis.py aufgerufen
    #macht BGT 24X BGT 2XX XXX 241

    #keine klasse vorhanden
    if not klassen:
        return "---"

    #nur eine klasse
    if len(klassen) == 1:
        return klassen[0]
    #gemeinsamer präfix finden
    prefix = klassen[0]
    for k in klassen[1:]:
        while not k.startswith(prefix):
            prefix = prefix[:-1]
            if not prefix:
                print(f"LEER: {klassen}", flush=True)
                return "XXXXXX"
    #add X
    laenge = len(klassen[0])
    fehlend = laenge - len(prefix)
    return prefix + "X" * min(fehlend, 6)

def raum_change(classroom: str, raum: str) -> str | None:
    if classroom == raum:
        return classroom
    if not classroom == raum:
        return raum + "->" + classroom
