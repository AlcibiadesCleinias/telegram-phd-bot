# telegram-phd-bot

A Telegram bot that acts as an AI-powered research assistant, leveraging OpenAI's GPT and DALL-E models.
<!-- TODO: add perplexity -->

#telegramPhdBot
#aiogram==3.2.0 
#ChatGPT 
#OpenAI

---
TODO: agenda


---

# Feature

## ChatGPT Integration
- Automatically responds to messages based on [triggers](bot/src/bot/consts.py):
  - Text length > 350 characters
  - Messages ending with "..." or ":"
  - Direct mentions (e.g. `@MiptPhDBot, I could not be sure that SUSY is not exist anymore`)
  - Replies to bot messages
  - Messages containing question marks
- Maintains conversation context for natural dialogue
- Supports both completion and chat models of OpenAI

> Under the hood it uses **completion model** and **chatGPT** as chat completion model. 
The last one is chosen only when there is a **dialog context exists**, i.e. it is possible to get previous context (message has replay_to and this source message is in the redis cache).

## Image Generation
- Creates images using DALL-E based on text prompts
- Supports direct commands and replies
- Automatically refines image prompts for academic context

## Access Level to Features

1. **Priority Chats**
   - Full access to AI features
   - Automatic response to triggers
   - Uses bot's primary OpenAI token

2. **Contributor**
   - Users can add their own OpenAI tokens
   - Personalized AI features in specified chats for only to be used by the contributor
   - Token management through `/add_openai_token` command

3. **Superadmin**
   - Access to AI features when iteract with bot in any chats
   - Broadcast messages (with media) to all bot aknowledged chats, except excluded ones
   - View usage statistics
   - Chat statistics and anonymised monitoring
   - Token usage tracking
   - Access additional administrative commands

4. **Basic**
   - Chat ID lookup
   - Help commands
   - Basic message responses (echo)

## Chat Management
- Automatic chat tracking
- Welcome messages for new members
- Message caching for context (TODO: do not cache messages where you do not have possiblity to use AI features)
- Support for both private and group chats

## Administrative Feature
Via env it is possible to configure:
- Configure chat exclusions for PhD periodic job and broadcast messages
- Configure priorty chats
- Configure superadmins

## Contributor Feature
For priorty chats it uses a special `TokenApiRequestManager` request engine with relay on main token and tokens of contributors. The idea was to add possibility to contribute free trial tokens to the bot to unlock unlimitted power of AI in several prioritised chats. Though, today idea is kind of dead, because there are no free trial tokens, and also we used to use our own private tokens nowadys as them not costs to much.

## Jobs
- send work result via cronjob to recently active chats & priority chats according to bot_chat_messages_cache. To exclude you should be in [phd work excluded chats, i.e. `TG_PHD_WORK_EXCLUDE_CHATS` env variable].

# Getting Started

## Run Bot Backend
Prepare `.env` as in `.example.env` and start with docker compose orchestrator.

> full env that is used you could find in [bot settings.py](bot/src/config/settings.py).

When env is ready, you could start bot backend with:
```bash
docker-compose up
```

### Run PhD Task Once
Optionally, (e.g. for debugging) you could run PhD task once:

```bash
docker-compose run bot --phd-work-notification-run-once
```

## Start Use Bot

1. Add the bot to your chat
2. Use `/help` to see available commands
3. For enhanced features:
   - Add your chats to priority chat list in env, or
   - Add your OpenAI token via `/add_openai_token`

# Usage Notes

- OpenAI features require either:
  - Being in a priority chat
  - Having contributor status with a valid OpenAI token
  - Superadmin
- Image generation requires additional OpenAI credits
- Message context is maintained for natural conversations. You could control depth of context fetching by according env (check env section). 
- All tokens are stored securely using encryption

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
To Develop you may use the same docker compose, merely do not forget **to rebuild always** after changes, e.g. `docker-compose up --build`. Or write your own docker-compose or override compose with volume mounting:
```
...
volumes:
  - ./bot/src:/opt
...
```
