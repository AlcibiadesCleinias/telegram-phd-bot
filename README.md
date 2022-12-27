# telegram-phd-bot
Bot does almost nothing and notifies about that gladly. No thanks, stonks pls.

# Feature
- send work result via cronjob
- echo to some messages
- send OPENAI completion to priority chats
- log other messages

# OpenAI Respons
It responses when
- chat id in a list,
- text length > 350 symbols,
- ends with ('...', '..', ':'),
- with bot mentioned,
- replied on a bot message,
- text with question mark (?)

# Run
Prepare `.env` as in `.example.env` and start with docker compose orchestrator.
## Cronjob
```bash
docker-compose up
```

## Run PhD Task Once
```bash
docker-compose run bot --phd-work-notification-run-once
```
