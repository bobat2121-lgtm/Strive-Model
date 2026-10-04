"""Strive's own definitions, as its treasury dashboard (strive.com/treasury) computes them. Values in brackets are the
dashboard's on 10/4/26 (ASST $30.03, BTC $85,224.79); tests/test_metrics.py pins every one.

    BTC NAV ("Bitcoin FMV")         = BTC held x BTC price                                   [$2.34B]
    Treasury Asset Value (TAV)      = BTC NAV + cash + marketable securities (STRC)          [$2.64B]
    Net Treasury Asset Value (NTAV) = TAV - debt - preferred liquidation preference          [$1.42B]
    NTAV per share                  = NTAV / assumed fully diluted shares                    [$14.09]
    mNAV                            = ASST price / NTAV per share                            [2.13x]  <- the model's multiple
    Enterprise Value                = FD shares x price + debt + preferred - cash - securities [$3.95B]
    EV / TAV                                                                                 [1.50x]
    EV / BTC NAV                    (the API's "evMnav" field)                               [1.69x]
    Common equity accretion premium = FD market cap / BTC NAV - 1                            [29.3%]
    Amplification                   = (debt + preferred notional) / BTC NAV                  [52.1%]
    Total dividend coverage (years) = TAV / annual SATA dividends                            [16.6]

SATA's liquidation preference is its $100 stated amount while it trades at par, so preferred = notional throughout.
Every function takes any object with btc, btc_price, fd_shares, sata_notional, cash, securities and debt (State, Book).
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Book:
    """The balance-sheet figures every metric needs, at one BTC price."""
    btc: float
    btc_price: float
    fd_shares: float
    sata_notional: float
    cash: float
    securities: float
    debt: float = 0.0


def btc_nav(b) -> float:
    return b.btc * b.btc_price


def tav(b) -> float:
    return btc_nav(b) + b.cash + b.securities


def ntav(b) -> float:
    return tav(b) - b.debt - b.sata_notional


def ntav_per_share(b) -> float:
    return ntav(b) / b.fd_shares


def mnav(b, price: float) -> float:
    return price / ntav_per_share(b)


def price_at(b, m: float) -> float:
    """The ASST price at which mNAV equals m."""
    return m * ntav_per_share(b)


def enterprise_value(b, price: float) -> float:
    return b.fd_shares * price + b.debt + b.sata_notional - b.cash - b.securities


def ev_to_tav(b, price: float) -> float:
    return enterprise_value(b, price) / tav(b)


def ev_to_btc_nav(b, price: float) -> float:
    return enterprise_value(b, price) / btc_nav(b)


def accretion_premium(b, price: float) -> float:
    """How far the FD market cap sits above BTC NAV; issuing common below this premium dilutes BTC per share."""
    return b.fd_shares * price / btc_nav(b) - 1


def amplification(b) -> float:
    return (b.debt + b.sata_notional) / btc_nav(b)


def sats_per_share(b) -> float:
    return b.btc / b.fd_shares * 1e8


def dividend_coverage_years(b, sata_rate: float) -> float:
    annual = sata_rate * b.sata_notional
    return tav(b) / annual if annual else math.inf


def summary(b, price: float, sata_rate: float) -> dict:
    return {"btc_nav": btc_nav(b), "tav": tav(b), "ntav": ntav(b), "ntav_per_share": ntav_per_share(b),
            "mnav": mnav(b, price), "enterprise_value": enterprise_value(b, price), "ev_to_tav": ev_to_tav(b, price),
            "ev_to_btc_nav": ev_to_btc_nav(b, price), "accretion_premium": accretion_premium(b, price),
            "amplification": amplification(b), "sats_per_share": sats_per_share(b),
            "dividend_coverage_years": dividend_coverage_years(b, sata_rate),
            "annual_dividends": sata_rate * b.sata_notional}
