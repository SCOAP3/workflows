import random


def generate_mapping_key():
    key = ''
    possible_chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    for i in range(5):
        key += possible_chars[random.randint(0, len(possible_chars) - 1)]
    return key

