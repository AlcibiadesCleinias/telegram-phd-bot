# telegram-phd-bot
Bot does almost nothing and notifies about that gladly. No thanks, stonks pls.

# Feature
Bot features depends on the next Telegram actors:
- **priority chats** - with triggers described below; (+ channels)
- **chats**
- **superadmin trigger** - in any chat, but not in channel

and for only 1 feature there is
- phd work excluded chats (check `TG_PHD_WORK_EXCLUDE_CHATS`)

Below is features and actors for each of them
- [priority chats, chats] send work result via cronjob. To exclude you should be in [phd work excluded chats]
- [priority chats, chats] echo to some messages
- [priority chats, superadmin trigger] send **OpenAI completion** to priority chats on some triggers
- [priority chats, superadmin trigger] support dialog with help of **OpenAI gpt-3**.
- [priority chats, chats] because of the above: it stores message model in redis (`redis.pipe` transactions)
  - log bot messages
  - log other messages
- [ ] [priority chats, chats] TODO: add possibility to store random user token: thus, activate openaAi feature (abuse other tokens like in fRPC)

## Priority Forwarding
- Bot runs on its own OpenAI token, however you could add him your token and with this

## OpenAI Response Trigger
It responses when:

- chat id in the [priority chats] list and:
  - text length > 350 symbols,
  - ends with ('...', '..', ':'),
  - bot is mentioned,
  - replied on a bot message,
  - text with question mark (?)
- superadmin messages into [priority chats, chats] and:
  - bot is mentioned,
  - replied on a bot message,

Under the hood it uses **completion model** and **chatGPT** as chat completion model. 
The last one is chosen only when there is a **dialog context exists**, i.e. it is possible to get previous context (message has replay_to and this source message is in the redis cache).

| You could control depth of context fetching by according env (check env section). 

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
