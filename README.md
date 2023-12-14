# telegram-phd-bot
Bot does almost nothing and notifies about that gladly. No thanks, stonks pls.

#telegramPhdBot
#aiogram==3.2.0 
#ChatGPT 
#OpenAI

---

* [Feature](#feature)
   * [Actors](#actors)
   * [Features to Actors](#features-to-actors)
      * [OpenAI Response Trigger](#openai-response-trigger)
* [Run](#run)
   * [Cronjob](#cronjob)
   * [Run PhD Task Once](#run-phd-task-once)
* [TODO](#todo)
* [Develop](#develop)

---

# Feature

## Actors
Bot features depends on the next **Telegram actors**:
- **[priority chats]** - with triggers described below; (+ channels)
- **[chats]** - to where bot was merely added
- **[chat-admin-rights]** - group chats with admin rights for the bot
- **[superadmin trigger]** - in any chat, but not in a channel (where is impossible to identify message sender)
- **[contributor chat]** - the phd bot runs with its own OpenAI token (defined in `.env`). However, anyone could supply to bot his own token and thus, activate openAI features for yourself or even for the chat where **bot has already existed** (even if the chat not in [priority chats]). Ref to command `add_openai_token` in the bot menu.
- [chats] bot is alive and could appreciate when you add PhD bot to the chat

and for only 1 feature there is
- phd work excluded chats (check `TG_PHD_WORK_EXCLUDE_CHATS`)

## Features to Actors
Below is features and actors map:
- **[priority chats, chats]** send work result via cronjob. To exclude you should be in [phd work excluded chats]
- **[priority chats, chats]** echo to some messages
- **[chats, chat-admin-rights]** greeting new bots, new members.
- **[priority chats, superadmin trigger, contributor chat]** send **OpenAI completion** to chats on some triggers by rotating all tokens about which bot knows. Here it uses special `TokenApiRequestManager` with relay on main token and tokens of contributors.
- **[priority chats, superadmin trigger, contributor chat]** support dialog with help of **OpenAI gpt-3**.
- **[priority chats, chats]** because of the above: it stores message model in redis (`redis.pipe` transactions)
  - log bot messages
  - log other messages
- **[chats]** get **chat id** by command
- **[chats]** even random user could get access to the OpenAI features by providing his token to the bot and open access to OpenAI ChatGPT feature in telegram.

| Additionally, bot stores all tokens cryptographically in the Redis db. 

### OpenAI Response Trigger
It responses when:

- chat id in the [priority chats] list and:
  - text length > 350 symbols,
  - ends with ('...', '..', ':'),
  - with bot mentioned via @,
  - replied on a bot message,
  - text consists of question mark (?)
- superadmin messages into [priority chats, chats] and:
  - bot is **mentioned** (e.g. `@MiptPhDBot, SUSY is not exist anymore`),
  - **replied** on a bot message,

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

# TODO
- [ ] store tokens with ciphering
- [ ] reuse fetched data in handlers from filters
- [ ] notify user when token does not work
- [ ] add request admin right on join
- [ ] add superadmin stats fetch
- [ ] trigger commands only on bot mentioned

# Develop
To Develop you may use the same docker compose, merely do not forget **to rebuild always** after changes, e.g. `docker-compose up --build`. Or write your own docker-compose with volume mounting.
