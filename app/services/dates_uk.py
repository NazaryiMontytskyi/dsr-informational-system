from datetime import date

MONTHS_GENITIVE = {
    1: "січня",
    2: "лютого",
    3: "березня",
    4: "квітня",
    5: "травня",
    6: "червня",
    7: "липня",
    8: "серпня",
    9: "вересня",
    10: "жовтня",
    11: "листопада",
    12: "грудня",
}


def day_month_year(d: date) -> tuple[str, str, str]:
    return str(d.day), MONTHS_GENITIVE[d.month], str(d.year)


def format_long_date(d: date) -> str:
    day, month, year = day_month_year(d)
    return f"«{day}» {month} {year} року"


def format_order_reference(order_number: str | None, order_date: date | None) -> str:
    if not order_number or not order_date:
        return "№ ____ від «____» ___________ 20__ р."
    day, month, year = day_month_year(order_date)
    return f"№ {order_number} від «{day}» {month} {year} року"
