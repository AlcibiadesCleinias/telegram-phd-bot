# telegram-phd-bot
Bot does almost nothing and notifies about that gladly. No thanks, stonks pls.

# Feature
- send work result via cronjob
- echo to some messages
- send **OPENAI completion** to priority chats
- log other messages

## OpenAI Response
It responses when
- chat id in a list and:
  - text length > 350 symbols,
  - ends with ('...', '..', ':'),
  - bot is mentioned,
  - replied on a bot message,
  - text with question mark (?)
- superadmin messages and:
  - bot is mentioned,

| Note, when combine response, it searches for replied messages with depth of 2.

| From OpenAI you may need API access token: https://platform.openai.com/account/usage (18-5 USD for a fresh new account usage).

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
