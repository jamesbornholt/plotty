from django import template

register = template.Library()

def dicthash(obj, hash):
    if hash in obj:
        return obj[hash]
    else:
        return None

register.filter('hash', dicthash)