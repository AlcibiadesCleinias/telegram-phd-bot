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

## Handlers
When bot recieves message it push the message through chain of registered filters/handlers. The following general filters are used:

- **[priority chats]** - if the message send to priority chat by anyone, and conssits of triggers described below; (+ channels)
- **[iteracted by superadmin]** - if the message send in any chat by superadmin to iteract with the phd bot (but not in a channel where is impossible to identify message sender though)
- **[iteracted by contributor]** - normally the phd bot runs with its own OpenAI token (defined in `.env`), however, anyone could supply to bot his own token and thus, activate openAI features for yourself in chats (become ChatGpt contributor for that chat). Ref to command `/add_openai_token` in the bot menu.
- **[chats]** - if the message send to any chat by anyone and that such handlers also are registered.
- **[command]** - if the message is a command, i.e. starts with `/start`

To note, there also other general purpose simple filters exists.

## Handlers to Features
Below is features and handlers map:

- **[priority chats, iteracted by superadmin, iteracted by contributor]** - The bot sends **OpenAI completion** to chats on ChatGpt triggers [triggers](bot/src/bot/consts.py). When **[priority chats]** filter used the bot tries to use one of the tokens it knows about and rotats if there are no success. Here it uses special `TokenApiRequestManager` with relay on main token and tokens of contributors.
- **[priority chats, iteracted by superadmin, iteracted by contributor]** - The bot supports dialog with help of **OpenAI gpt-3**.
- **[priority chats, iteracted by superadmin, iteracted by contributor, command]** - Now it is possible to use OpenaAI DellE model to generate image from prompt.  
- **[chats]** because of the above: the bot stores messages in redis (`redis.pipe` transactions)
  - log bot messages
  - log other messages
- **[chats]** echo to some messages
- **[chats]** greeting new bots, new members.
- **[chats, command]** get **chat id** by command
- **[chats, command]** bot is alive and could appreciate when you add PhD bot to the chat
- **[iteracted by superadmin, command]** superadmin commands like: [commands/admin](bot/src/bot/handlers/commands/admin)
  - TODO: there should description for admin commands

| Additionally, bot stores all tokens cryptographically in the Redis db. 

# Jobs
- send work result via cronjob to recently active chats & priority chats according to bot_chat_messages_cache. To exclude you should be in [phd work excluded chats, i.e. `TG_PHD_WORK_EXCLUDE_CHATS` env variable].

### OpenAI Response Trigger
It responses when one of the trigger is fulfilled from [triggers](bot/src/bot/consts.py). Or by plain text:

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
- [x] store tokens with ciphering
- [ ] reuse fetched data in handlers from filters
- [x] notify user when token does not work
- [ ] add request admin right on join
- [x] add superadmin stats fetch
- [x] broadcast message from superadmin (ignore chats?)
- [x] TODO: aiogram.exceptions.TelegramBadRequest: Telegram server says - Bad Request: message is too long
- [ ] add service task to delete all keys with expired `updated_chat_ttl`.

# Develop
To Develop you may use the same docker compose, merely do not forget **to rebuild always** after changes, e.g. `docker-compose up --build`. Or write your own docker-compose with volume mounting.
