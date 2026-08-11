import sys

from nova.agent import chat_text, chat_voice

if __name__ == "__main__":
    if "--voice" in sys.argv:
        chat_voice()
    else:
        chat_text()
