# rjdap

## UDP INIT/DATA prototype

DEMO Video Link: https://drive.google.com/file/d/1QOvAKRsMP8VZ33LPmMsCFijljELs_e5d/view?usp=sharing

This Phase 1 prototype uses only the Python standard library. The server and
client exchange CRC-protected binary UDP packets with a fixed 22-byte header:

1. The client sends `INIT`; the server replies with `INIT_ACK` and assigns a
   worker ID.
2. The client sends numbered `DATA` messages; the server replies with
   `DATA_ACK`.
3. The client retries an exchange when an acknowledgement is not received.
4. Both processes write timestamped CSV event logs.

Run a single exchange from the repository root:

```powershell
py scripts\demo_task_manager.py
```

Run the automated **Baseline local** scenario (one server, four clients, 1,000
deterministic DATA messages):

```powershell
py scripts\run_baseline.py
```

The script prints `BASELINE_PASS` and writes `results\baseline\server.csv` plus
one CSV log per client. To run the components separately:

```powershell
py src\server.py --port 9000 --expected-data 1 --log results\server.csv
py src\client.py --port 9000 --name local --count 1 --log results\client.csv
```

Use `--port` to choose another local UDP port if 9000 or 9001 is occupied.

## Checklist

- [x] Server and client run locally over UDP.
- [x] INIT and DATA exchanges are acknowledged.
- [x] CRC-32 validation and bounded retransmission are demonstrated.
- [x] Timestamped CSV logs are produced.
- [x] `scripts\run_baseline.py` automates the Baseline local test.
