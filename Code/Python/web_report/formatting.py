"""Formati di sola presentazione: importi compatti, dati ed export invariati."""
from data_model import fmt


def money_scale(values):
    """Scala comune per gli assi di un grafico; il segno non cambia la scala."""
    largest = max((abs(value) for value in values if value is not None), default=0)
    return (1_000_000, "M€") if largest >= 1_000_000 else (1_000, "k€")


def money(value):
    if value is None:
        return "Non applicabile"
    divisor, unit = money_scale([value])
    return f"{fmt(value / divisor, 1)} {unit}"
