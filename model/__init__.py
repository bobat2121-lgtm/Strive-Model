"""Strive (ASST) model: one weekly engine driven by four levers.

    sources/     where numbers come from (strive.com, the weekly 8-K feed, Coinbase, Yahoo), cached as last-good copies
    state.py     the company today, as one dated snapshot
    metrics.py   Strive's own definitions: mNAV (EV / BTC NAV), amplification, sats per share, net BPS, coverage
    levers.py    the four levers (BTC path, SATA per week, common % per week, mNAV) plus fixed assumptions
    engine.py    the weekly projection
    valuation.py the mNAV x BTC CAGR price table and the four-part attribution
    calibrate.py weekly issuance backed out of 8-K share counts and VWAP (what the lever defaults are based on)
"""
