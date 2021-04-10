import switchmate
import time

# Find any switchmates in bluetooth range
switchmates = switchmate.scan(timeout=int(5))

# Init
switchmates[0].update()

# Turn the first one on
switchmates[0].turn_on()

# Wait
print('sleeping for 5 seconds')
time.sleep(5)

# Turn it off
switchmates[0].turn_off()
