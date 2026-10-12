import json
import os
from datetime import datetime, date

PATH = os.getenv('BIRTHDAYS_PATH', 'birthdays.json')

# Year is optional; when omitted a leap year is assumed so 29/02 is valid.
FORMATS = ('%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y')
FORMATS_NO_YEAR = ('%d/%m', '%d-%m', '%d.%m')


def load() -> dict:
    if os.path.exists(PATH):
        with open(PATH) as f:
            return json.load(f)
    return {}


def save(data: dict):
    with open(PATH, 'w') as f:
        json.dump(data, f, indent=2)


def parse(text: str):
    text = text.strip()
    for fmt in FORMATS:
        try:
            d = datetime.strptime(text, fmt)
            return f'{d.month:02d}-{d.day:02d}'
        except ValueError:
            continue
    for fmt in FORMATS_NO_YEAR:
        try:
            d = datetime.strptime(text + '/2000', fmt + '/%Y')
            return f'{d.month:02d}-{d.day:02d}'
        except ValueError:
            continue
    return None


def set_birthday(user_id, text):
    mmdd = parse(text)
    if mmdd is None:
        return None
    data = load()
    data[str(user_id)] = mmdd
    save(data)
    return mmdd


def get_birthday(user_id):
    return load().get(str(user_id))


def birthdays_on(month, day):
    mmdd = f'{month:02d}-{day:02d}'
    return [uid for uid, value in load().items() if value == mmdd]


def next_birthday(from_date=None):
    from_date = from_date or date.today()
    best = None
    for uid, mmdd in load().items():
        month, day = int(mmdd[:2]), int(mmdd[3:])
        try:
            candidate = date(from_date.year, month, day)
            if candidate < from_date:
                candidate = date(from_date.year + 1, month, day)
        except ValueError:
            continue  # e.g. 29/02 in a non-leap year
        if best is None or candidate < best[1]:
            best = (uid, candidate)
    return best


def clear_birthday(user_id):
    data = load()
    if data.pop(str(user_id), None) is not None:
        save(data)
        return True
    return False


def _demo():
    global PATH
    import tempfile
    original, tmp = PATH, tempfile.mktemp(suffix='.json')
    PATH = tmp
    try:
        assert parse('29/02') == '02-29'
        assert parse('1-1') == '01-01'
        assert parse('15.08.1995') == '08-15'
        assert parse('nope') is None
        assert get_birthday(1) is None
        assert set_birthday(1, '24/12') == '12-24'
        assert get_birthday(1) == '12-24'
        assert clear_birthday(1) is True
        assert get_birthday(1) is None
        set_birthday(2, '24/12')
        assert birthdays_on(12, 24) == ['2']
        assert birthdays_on(12, 25) == []
        assert next_birthday(date(2026, 1, 1)) == ('2', date(2026, 12, 24))
        assert next_birthday(date(2026, 12, 25)) == ('2', date(2027, 12, 24))
        assert next_birthday(date(2026, 12, 24)) == ('2', date(2026, 12, 24))
        print('Birthdays demo OK')
    finally:
        PATH = original
        if os.path.exists(tmp):
            os.remove(tmp)


if __name__ == '__main__':
    _demo()
