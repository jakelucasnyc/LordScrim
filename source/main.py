import logging
import bot
logging.basicConfig(level=logging.INFO)

def readToken():
    with open('bot/secrets/bot.token') as f:
        token = f.read()
        return token

if __name__ == '__main__':
    try:
        token = readToken()
        scrim = bot.bot
        scrim.run(token)
    except Exception as e:
        logging.exception(f'Program Crashed: {e}')

    else:
        logging.info('Process complete') 