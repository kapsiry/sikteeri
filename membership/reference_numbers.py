def generate_checknumber(number):
    check = 0
    checks = [7, 3, 1]
    for i, digit in enumerate(reversed(number)):
        check += checks[i%3]*int(digit)
    return (10 - check%10)%10

def add_checknumber(number):
    return number + generate_checknumber(number)
