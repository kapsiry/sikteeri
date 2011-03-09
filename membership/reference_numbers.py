# -*- coding: utf-8 -*-

def generate_membership_bill_reference_number(membership_id, bill_year):
    # [jäsennumero] yyxxz
    # jossa yy=vuosi kahdella numerolla, xx=maksutapahtumakoodi ja z tarkistenumero
    # 01 on ollut perinteisesti jäsenmaksun maksutapahtumakoodi
    bill_type_suffix = "01"

    return add_checknumber("%i%s%s" % \
                           (membership_id,
                            str(bill_year)[-2:],
                            bill_type_suffix))

def generate_checknumber(number):
    check = 0
    checks = [7, 3, 1]
    for i, digit in enumerate(reversed(number)):
        check += checks[i%3]*int(digit)
    return (10 - check%10)%10

def add_checknumber(number):
    return number + str(generate_checknumber(number))

def group_right(number, group_size = 5):
    number = number.replace(" ", "")
    groups = []
    while number:
        groups.insert(0, number[-group_size:])
        number = number[:-group_size]
    return " ".join(groups)
