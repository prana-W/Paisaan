import sys
import os
sys.path.append(os.path.abspath("."))
from app.agent.graph import _parse_user_consent

print("Testing parsing:")
print(_parse_user_consent("ok continue"))
