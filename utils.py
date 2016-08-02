
"""
Replace characters in a string
"""
def str_replace_chars(text, chars_origine, chars_replace):
    for i in range(len(chars_origine)):
        text2 = text.replace(chars_origine[i], chars_replace[i])
        text  = text2
    return text2

def replace_accents(text):
    chars_origine = ['\xC3','\xE0', '\xE1', '\xE2', '\xE3', '\xE4', '\xE5',
                      '\xE6', '\xE7', '\xE8', '\xE9', '\xEA', '\xEB', '\xEC',
                      '\xED', '\xEE', '\xEF', '\xF2', '\xF3', '\xF4', '\xF5',
                      '\xF6', '\xF9', '\xFA', '\xFB', '\xFC']
    chars_replace = ['E', 'a', 'a', 'a', 'a', 'a', 'a', 'ae', 'c', 'e', 'e',
                     'e', 'e', 'i', 'i', 'i', 'i', 'o', 'o', 'o', 'o', 'o',
                     'u', 'u', 'u', 'u']
    text2 = str_replace_chars(text, chars_origine, chars_replace)
    return text2
