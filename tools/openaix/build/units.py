"""Metre conversion factors for the shared Length and Altitude units."""

LENGTH_UNITS = {"m": 1, "ft": 0.3048, "nm": 1852, "km": 1000}
ALTITUDE_UNITS = {"ft": 0.3048, "m": 1, "flight_level": 30.48}
# Radio bands as aviation radios use them, with their limits in megahertz (lower inclusive, upper exclusive):
# HF, VHF-FM (the military FM band), the VHF airband and the military UHF band. checks_navigation.frequency_band
# compares a stated band with the frequency value.
RADIO_BANDS = {"hf": (2, 30), "fm": (30, 88), "vhf": (108, 174), "uhf": (225, 400)}
