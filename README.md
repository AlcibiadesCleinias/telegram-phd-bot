# telegram-phd-bot
Bot does almost nothing and notifies about that gladly. No thanks, stonks pls.

# Feature
- send work result via cronjob
- echo to some messages
- send **OPENAI completion** to priority chats on some triggers
- support dialog with help of **OPENAI gpt-3**.
- because of the above: it stores message model in redis (`redis.pipe` transactions)
- log other messages
- log bot messages
- [ ] TODO: add possibility to store random user token: thus, activate openaAi feature (abuse other tokens like in fRPC)  

## OpenAI Response
It responses when:

- chat id in a list and:
  - text length > 350 symbols,
  - ends with ('...', '..', ':'),
  - bot is mentioned,
  - replied on a bot message,
  - text with question mark (?)
- superadmin messages and:
  - bot is mentioned,
  - replied on a bot message,

Under the hood it uses **completion model** and **chatGPT**. 
The last one only when there is a **dialog context exists**.

| Note, when combine response, it searches for replied messages with depth of 2.

| From OpenAI you may need API access token: https://platform.openai.com/account/usage (18-5 USD for a fresh new account usage).

# Run
Prepare `.env` as in `.example.env` and start with docker compose orchestrator.

> full env that is used you could find in [bot settings.py](bot/src/config/settings.py).

## Cronjob
```bash
docker-compose up
```

## Run PhD Task Once
```bash
docker-compose run bot --phd-work-notification-run-once
```
