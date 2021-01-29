This is a script that reads [GBFS](https://github.com/NABSA/gbfs) data on available bikes from a city
(uses [free_bike_status.json](https://github.com/NABSA/gbfs/blob/v1.0/gbfs.md#free_bike_statusjson)
and [station_information.json](https://github.com/NABSA/gbfs/blob/v1.0/gbfs.md#station_informationjson))
and outputs a json file describing trips made during the time the script ran.

Note that this uses the bike_id field, which means it won't work if IDs are changed (mandatory starting with GBFS 2.0).

`python3 main.py` to run, tested with python 3.9.1 on the Berlin Nextbike network. To use another provider, change the
URLs at the bottom of main.py or create another BikeRegistry.

Output is written after a KeyboardInterrupt (<kbd>Ctrl</kbd> + <kbd>C</kbd>) into data.json. and looks like this:

```
[
    {
        "started_at": "2021-01-29 19:06:03+00:00",
        "ended_at": "2021-01-29 20:34:30+00:00",
        "duration": 5307,
        "start_station_id": 0,
        "start_station_name": "Flex parking",
        "start_station_latitude": 52.485791111111,
        "start_station_longitude": 13.434968888889,
        "end_station_id": 0,
        "end_station_name": "Flex parking",
        "end_station_latitude": 52.485293333333,
        "end_station_longitude": 13.428682222222
    },
    {
        "started_at": "2021-01-29 19:09:07+00:00",
        "ended_at": "2021-01-29 19:16:13+00:00",
        "duration": 426,
        "start_station_id": 0,
        "start_station_name": "Flex parking",
        "start_station_latitude": 52.495253333333,
        "start_station_longitude": 13.457843333333,
        "end_station_id": 0,
        "end_station_name": "Flex parking",
        "end_station_latitude": 52.500315555556,
        "end_station_longitude": 13.466012222222
    },
...
]
```
