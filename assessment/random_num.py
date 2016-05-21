import random


# Supposed given function
def random5():
    """
    Generates a random number from 1 to 5
    """
    return random.randint(1, 5)


def random7():
    """
    Creates a random number from 1 to 7
    """
    num = (random5() + random5()) % 7 + 1
    return num
