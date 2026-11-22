"""Read orders from the Luna parent portal."""

from dataclasses import dataclass, field
from datetime import date, timedelta
from html.parser import HTMLParser
from http.cookiejar import CookieJar
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import (
    HTTPCookieProcessor,
    HTTPRedirectHandler,
    Request,
    build_opener,
)

ORIGIN = "https://bestellen.luna.de"
ORDER_DATA_PATH = "/order/load-data"
MONTHS = (
    "Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
    "September", "Oktober", "November", "Dezember",
)
VOID_TAGS = frozenset(
    "area base br col embed hr img input link meta param source track wbr".split()
)


class LunaError(Exception):
    """Luna could not supply a verified order list."""


class LunaAuthError(LunaError):
    """Luna did not accept the account credentials."""


@dataclass
class Element:
    tag: str
    attrs: dict[str, str | None] = field(default_factory=dict)
    children: list["Element | str"] = field(default_factory=list)

    @property
    def elements(self):
        return (item for item in self.children if isinstance(item, Element))

    @property
    def text(self) -> str:
        if self.tag == "br":
            return " "
        return "".join(
            item.text if isinstance(item, Element) else item for item in self.children
        )

    def find(self, tag: str):
        for child in self.elements:
            if child.tag == tag:
                yield child
            yield from child.find(tag)


class Document(HTMLParser):
    def __init__(self, markup: str) -> None:
        super().__init__()
        self.root = Element("document")
        self.stack = [self.root]
        self.feed(markup)
        self.close()

    def handle_starttag(self, tag, attrs):
        element = Element(tag, dict(attrs))
        self.stack[-1].children.append(element)
        if tag not in VOID_TAGS:
            self.stack.append(element)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def normalize(text: str) -> str:
    return " ".join(text.split())


def order_months(today: date) -> tuple[date, date]:
    first = today.replace(day=1)
    return first, (first + timedelta(days=32)).replace(day=1)


def table_rows(table: Element):
    for element in table.elements:
        if element.tag == "tr":
            yield element
        elif element.tag in {"thead", "tbody", "tfoot"}:
            yield from (row for row in element.elements if row.tag == "tr")


def parse_orders(page: Element, month: date) -> dict[date, str]:
    title = next(page.find("title"), Element("title")).text
    month_name = MONTHS[month.month - 1]
    if not title.startswith(f"Bestellungen - {month_name} {month.year} - "):
        raise LunaError("Luna returned a page for an unexpected month.")

    outer = next(page.find("table"), None)
    if outer is None:
        raise LunaError("The Luna order table is missing.")
    rows = iter(table_rows(outer))
    header = next(rows, Element("tr"))
    if [normalize(cell.text) for cell in header.elements] != ["Mo", "Di", "Mi", "Do", "Fr"]:
        raise LunaError("The Luna order table has an unexpected format.")

    meals = {}
    for week in rows:
        for day in week.elements:
            menu = next(day.find("table"), None)
            if menu is None:
                continue
            number = normalize(next(day.elements, Element("div")).text)
            try:
                meal_date = month.replace(day=int(number))
            except ValueError:
                raise LunaError("The Luna order table contains an invalid date.") from None
            ordered = []
            for row in table_rows(menu):
                cells = [normalize(cell.text) for cell in row.elements]
                marks = [cell for cell in cells if cell in {"●", "○"}]
                if len(marks) != 1:
                    raise LunaError("A Luna dish has an unknown order status.")
                if marks == ["●"]:
                    ordered.append(" ".join(cell for cell in cells if cell != "●"))
            if ordered:
                if meal_date in meals or not all(ordered):
                    raise LunaError("The Luna table contains an ambiguous order.")
                meals[meal_date] = " / ".join(ordered)
    return meals


def luna_url(base: str, target: str) -> str:
    url = urljoin(base, target)
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.netloc != "bestellen.luna.de":
        raise LunaError("Luna returned an unexpected destination.")
    return url


class LunaRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req, fp, code, msg, headers, luna_url(req.full_url, newurl))


class LunaPortal:
    """Use a dedicated, in-memory cookie jar for the configured account."""

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password
        self.cookies = CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.cookies), LunaRedirectHandler())

    def _fetch(
        self,
        path: str,
        data: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[str, str]:
        request = Request(
            luna_url(ORIGIN, path),
            data=urlencode(data).encode() if data is not None else None,
            headers=headers or {},
        )
        try:
            with self.opener.open(request, timeout=12) as response:
                body = response.read(2_000_001)
                if len(body) > 2_000_000:
                    raise LunaError("The Luna page is larger than expected.")
                encoding = response.headers.get_content_charset() or "utf-8"
                return response.url, body.decode(encoding)
        except (HTTPError, URLError, TimeoutError, UnicodeError, LookupError):
            raise LunaError("The Luna parent portal could not be reached or read.") from None

    def _request(self, path: str, data: dict[str, str] | None = None) -> tuple[str, Element]:
        url, markup = self._fetch(path, data)
        return url, Document(markup).root

    def selection_month(self, month: date) -> object:
        """Read the same calendar data as the parent's booking view."""
        url, body = self._fetch(
            ORDER_DATA_PATH,
            {"month": f"{month.year}-{month.month}-01"},
            {"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"},
        )
        if urlsplit(url).path != ORDER_DATA_PATH:
            raise LunaError("Luna redirected the calendar data request.")
        try:
            return json.loads(body)
        except ValueError:
            raise LunaError("Luna did not return calendar data as JSON.") from None

    def _login(self, url: str, page: Element) -> None:
        for form in page.find("form"):
            fields = {node.attrs["name"]: node.attrs for node in form.find("input") if node.attrs.get("name")}
            passwords = [name for name, attrs in fields.items() if attrs.get("type") == "password"]
            if not passwords:
                continue
            names = [name for name, attrs in fields.items() if attrs.get("type", "text") in {"email", "text"}]
            if len(passwords) != 1 or len(names) != 1 or form.attrs.get("method", "").lower() != "post":
                break
            payload = {
                name: attrs.get("value") or "" for name, attrs in fields.items()
                if attrs.get("type") == "hidden"
            }
            payload.update({names[0]: self.username, passwords[0]: self.password})
            self._request(luna_url(url, form.attrs.get("action") or url), payload)
            return
        raise LunaError("The Luna login form has an unexpected format.")

    def orders(self, today: date) -> dict[date, str]:
        url, page = self._request("/order/")
        if urlsplit(url).path.rstrip("/") == "/login":
            self._login(url, page)
            url, page = self._request("/order/")
        if urlsplit(url).path.rstrip("/") == "/login":
            self.cookies.clear()
            raise LunaAuthError("Luna did not accept the sign-in.")

        selector = next(
            (node for node in page.find("select") if node.attrs.get("id") == "currentContract"),
            Element("select"),
        )
        contracts = [
            option
            for option in selector.find("option")
            if option.attrs.get("value") not in {None, "", "0"}
        ]
        if len(contracts) != 1:
            raise LunaError("Luna must have exactly one school-meal contract for this setup.")

        current, following = order_months(today)
        meals = {}
        for month in (current, following):
            path = f"/order/print-overview?date={month.isoformat()}"
            if not any(link.attrs.get("href") == path for link in page.find("a")):
                if month == following:
                    continue
                raise LunaError("The Luna link for the requested month is missing.")
            _, overview = self._request(path)
            meals.update(parse_orders(overview, month))
        return meals
