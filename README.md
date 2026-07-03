# Stock Analyst AI (Nifty 50 + Next 50)

Automated swing trading signals on Telegram. Runs free on **GitHub Actions**.

## Strategy

- Delivery swing: sell at **+3%** profit
- On **-3%** loss: average **30%** more (max 5 times)
- One **BUY** per day from Nifty 100 scan

## Loop Schedule (IST, Mon–Fri)

| Loop | Time | Action |
|------|------|--------|
| Morning | 8:40 AM | Full scan → **BUY** signal |
| Intraday | Every 30 min (9:15–3:15) | **SELL** / **AVERAGE** check |

## Telegram Commands

```
/buy TITAN    — after you buy in broker
/sell         — after selling
/average      — after averaging down
/status       — open position
/help
```

## GitHub Secrets Required

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## Manual Test

```bash
python run_loop.py
# or
JOB_MODE=morning python run_loop.py
JOB_MODE=intraday python run_loop.py
```