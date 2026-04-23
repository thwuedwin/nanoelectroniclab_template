# %%
# == Import ==

import requests
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from typing_extensions import (
        Unpack,  # can be imported from typing if python >= 3.12
    )

from datetime import datetime, timedelta, timezone

from qcodes.parameters import Parameter

# %%
class bluefors(Parameter):
    def __init__(self, name, host, ch):
        # only name is required
        super().__init__(
            name,
            label="Temperature",
            unit="k",
            docstring='''Get bluefors temperature throught controller API''',
        )
        self._host = host
        self._ch = ch

    # you must provide a get method, a set method, or both.
    def get_raw(self):

        def get_latest_channel_value(
            host: str,
            channel_nr: int,
            field: str = "temperature",
            lookback_seconds: int = 120,
            timeout: int = 10,
        ):
            """
            Use /channel/historical-data to fetch the most recent value of a given field for a channel.
            Returns: (timestamp, value) where timestamp is float seconds since epoch (from API), or None if no data.
            """
            url = f"http://{host}:5001/channel/historical-data"

            # API accepts "YYYY-MM-DDTHH:MM:SSZ" format
            stop_dt = datetime.now(timezone.utc)
            start_dt = stop_dt - timedelta(seconds=lookback_seconds)

            payload = {
                "channel_nr": channel_nr,
                "start_time": start_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "stop_time": stop_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "fields": ["timestamp", field],
            }

            r = requests.post(url, json=payload, timeout=timeout)
            data = r.json()

            if data.get("status") != "OK":
                raise RuntimeError(f"API error: {data}")

            meas = data.get("measurements", {})
            ts_list = meas.get("timestamp", [])
            val_list = meas.get(field, [])

            if not ts_list or not val_list:
                return None  # no data in this time window

            return val_list[-1]
    
        return get_latest_channel_value(self._host, self._ch, field='temperature')
    
# %%
if __name__ == '__main__':
    b = bluefors('mxc', '192.168.50.8', 7)
    print(b())

# %%
