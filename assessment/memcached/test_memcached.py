import random
import string
from sys import argv
from new_memcached import MemcacheClient


def random_key(size):
    """ Generates a random key
    """
    return ''.join(random.choice(string.letters) for _ in range(size))


if __name__ == '__main__':
    # Default algorithm
    algorithm = "ketama"

    if "-k" in argv or "-m" in argv:
        if argv[1] == "-m":
            algorithm = "modulo"
    else:
        print "\nPass \"-m\" for Modulo or \"-k\" for Ketama algorithm."
        print "The default algorithm is \"Ketama\"."

    # We have 7 running memcached servers
    servers = ['127.0.0.1:1121%d' % i for i in range(1, 8)]

    # We have 100 keys to split across our servers
    keys = [random_key(10) for i in range(100)]

    # Init our subclass
    client = MemcacheClient(servers=servers, hash_algorithm=algorithm)

    print(
        "\n/////////// CONSISTENT HASH ALGORITHM \"%s\" //////////////"
        "" % client.hash_algorithm.upper()
    )

    print("\n--> Starting with %s servers:" % len(servers))

    str_servers = ""
    for server in client.servers:
        str_servers += "%s:%s, " % (server.address[0], server.address[1])

    print("*******************************************************")
    print(str_servers)
    print("*******************************************************")

    # Distribute the keys on our servers
    for key in keys:
        client.set(key, 1)

    print(
        "\n%d keys distributed for %d server(s)\n"
        "" % (len(keys), len(servers))
    )

    # Check how many keys come back
    valid_keys = client.get_multi(keys)
    print '%s percent of keys matched, before adding extra server' % (
        (len(valid_keys)/float(len(keys))) * 100)

    # We add another server...and pow!
    client.add_server('127.0.0.1:11218')
    print '*--- Added new server ---*'

    valid_keys = client.get_multi(keys)
    print '%s percent of keys stil matched' % (
        (len(valid_keys)/float(len(keys))) * 100)

    str_servers = ""
    for server in client.servers:
        str_servers += "%s:%s, " % (server.address[0], server.address[1])

    print("\n********************************************************")
    print(str_servers)
    print("********************************************************")
