import json
from pathlib import Path

import pandas as pd
import pytest

from model import state as state_mod
from model.levers import Levers

FX = Path(__file__).parent / "fixtures"


@pytest.fixture
def calc():
    return json.loads((FX / "strive_calculated_2026-10-04.json").read_text())


@pytest.fixture
def base():
    return json.loads((FX / "strive_base_2026-10-04.json").read_text())["data"]


@pytest.fixture
def st(calc, base):
    """Strive's dashboard on 10/4/26 (the screenshot): 9/25 balance sheet, ASST $30.03, BTC $85,224.79."""
    return state_mod.from_payloads(calc, base).with_prices(85224.79, 30.03)


@pytest.fixture
def lv():
    return Levers()  # the code defaults, which test_levers keeps equal to config/levers.yaml


@pytest.fixture
def feed():
    return json.loads((FX / "feed_2026-10-04.json").read_text())


@pytest.fixture
def bars():
    df = pd.read_csv(FX / "bars_2026-10-03.csv", parse_dates=["date"])
    return {t: g.drop(columns="ticker").set_index("date") for t, g in df.groupby("ticker")}
