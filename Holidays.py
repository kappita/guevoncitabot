import json
import os
import re
from datetime import date
from html.parser import HTMLParser

import requests

URL = 'https://www.feriados.cl/'
PATH = os.getenv('HOLIDAYS_PATH', 'holidays.json')

MONTHS = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'setiembre': 9, 'octubre': 10,
    'noviembre': 11, 'diciembre': 12,
}

DATE_RE = re.compile(r'(\d{1,2})\s+de\s+([a-záéíóú]+)', re.IGNORECASE)
YEAR_RE = re.compile(r'A[ñn]o\s+(\d{4})')


class _TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self._table = None
        self._row = None
        self._cell = None

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self._table = []
        elif tag == 'tr' and self._table is not None:
            self._row = []
        elif tag in ('td', 'th') and self._row is not None:
            self._cell = []

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self._cell is not None:
            self._row.append(' '.join(' '.join(self._cell).split()))
            self._cell = None
        elif tag == 'tr' and self._row is not None:
            self._table.append(self._row)
            self._row = None
        elif tag == 'table' and self._table is not None:
            self.tables.append(self._table)
            self._table = None


def load() -> list:
    if os.path.exists(PATH):
        with open(PATH) as f:
            return json.load(f)
    return []


def save(data: list):
    with open(PATH, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def parse(html: str) -> list:
    match = YEAR_RE.search(html)
    year = int(match.group(1)) if match else date.today().year

    parser = _TableParser()
    parser.feed(html)
    if not parser.tables:
        return []

    holidays = []
    for cells in parser.tables[0]:  # first table = national ("carácter general")
        if len(cells) < 2:
            continue
        m = DATE_RE.search(cells[0])
        month = MONTHS.get(m.group(2).lower()) if m else None
        if not month:
            continue
        day = int(m.group(1))
        title = cells[1].replace('Irrenunciable', '').strip()
        holidays.append({'date': f'{year:04d}-{month:02d}-{day:02d}', 'title': title})
    return holidays


def refresh() -> list:
    response = requests.get(URL, timeout=30, headers={'User-Agent': 'Mozilla/5.0'})
    response.raise_for_status()
    data = parse(response.text)
    save(data)
    return data


def on(day: str):
    for holiday in load():
        if holiday['date'] == day:
            return holiday['title']
    return None


def next_holiday(from_date=None):
    from_date = from_date or date.today()
    upcoming = sorted((h for h in load() if h['date'] >= from_date.isoformat()),
                      key=lambda h: h['date'])
    return upcoming[0] if upcoming else None


def _demo():
    global PATH
    import tempfile
    original, tmp = PATH, tempfile.mktemp(suffix='.json')
    PATH = tmp
    try:
        html = '''<h1>Feriados de Chile Año 2026</h1><table>
          <tr><th>Día</th><th>Festividad</th><th>Tipo</th><th>Legal</th></tr>
          <tr><td>Todos los Días Domingos</td><td>Día Domingo</td><td>Civil</td><td>Ley</td></tr>
          <tr><td>Jueves, 01 de Enero</td><td>Año Nuevo<br/><span>Irrenunciable</span></td><td>Civil</td><td>Ley</td></tr>
          <tr><td>Sábado, 31 de Octubre</td><td>Día de las Iglesias Evangélicas y<br>Protestantes</td><td>Religioso</td><td>Ley</td></tr>
        </table>'''
        result = parse(html)
        assert len(result) == 2, result
        assert result[0] == {'date': '2026-01-01', 'title': 'Año Nuevo'}, result[0]
        assert result[1] == {'date': '2026-10-31', 'title': 'Día de las Iglesias Evangélicas y Protestantes'}, result[1]

        save(result)
        assert on('2026-01-01') == 'Año Nuevo'
        assert on('2026-02-02') is None
        assert next_holiday(date(2026, 1, 1))['title'] == 'Año Nuevo'
        assert next_holiday(date(2026, 2, 1))['date'] == '2026-10-31'
        assert next_holiday(date(2027, 1, 1)) is None
        print('Holidays demo OK')
    finally:
        PATH = original
        if os.path.exists(tmp):
            os.remove(tmp)


if __name__ == '__main__':
    _demo()
