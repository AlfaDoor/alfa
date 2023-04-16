import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

official_workings = [
    {
        'work_start': "07:00",
        'work_end': "12:00",
        'allow_late': 15,
        'allow_previous': 10
    },
    {
        'work_start': "13:00",
        'work_end': "17:00",
        'allow_late': 15,
        'allow_previous': 10}]

actual_workings = [
    {
        'sign_in': "07:16",
        'sign_out': "11:49"},
    {

        'sign_in': "13:01",
        'sign_out': "17:00"}]


def over_time_calc(official_workings, actual_workings):
    working_minuets = []
    actual_working_minuets = []
    sings_in = sings_out = []
    for actual_working in actual_workings:
        actual_working_minuets += get_minuets_in_period(actual_working['sign_in'], actual_working['sign_out'])
        sings_in.append(actual_working['sign_in'])
        sings_out.append(actual_working['sign_out'])
    exclude_of_deduction = []
    for official_working in official_workings:
        max_signin = time_increase(official_working['work_start'], official_working['allow_late'] + 1)
        if max_signin in actual_working_minuets:
            exclude_of_deduction += get_minuets_in_period(official_working['work_start'], max_signin)
        min_signout = time_increase(official_working['work_end'], -official_working['allow_previous'] - 1)
        if min_signout in actual_working_minuets:
            exclude_of_deduction += get_minuets_in_period(min_signout, official_working['work_end'])
        working_minuets += get_minuets_in_period(official_working['work_start'], official_working['work_end'])
    all_day_minuets = get_minuets_in_period("00:00", "23:59")
    worked_minutes = []
    deduction_minutes = []
    overtime_minutes = []
    delay_minutes = []
    exit_minutes = []
    action = True
    for minuet in all_day_minuets:
        if minuet in sings_in:
            action = False
        minuet_official = minuet in working_minuets
        minuet_worked = minuet in actual_working_minuets
        if minuet_official and not minuet_worked and minuet not in exclude_of_deduction:
            deduction_minutes.append(minuet)
            print("################# deduction:%s" % minuet)
            if action:
                delay_minutes.append(minuet)
            else:
                exit_minutes.append(minuet)
        if minuet_worked and not minuet_official:
            overtime_minutes.append(minuet)
        if minuet_worked and minuet_official:
            worked_minutes.append(minuet)
        if not minuet_official and not minuet_worked:
            action = True
    res = {
        'overtime': minuets_to_time(len(overtime_minutes)),
        'deduction': minuets_to_time(len(deduction_minutes)),
        'working_minutes': minuets_to_time(len(worked_minutes)),
        'working_minutes_to': minuets_to_time(len(actual_working_minuets)),
        'delay_minutes': minuets_to_time(len(delay_minutes)),
        'exit_minutes': minuets_to_time(len(exit_minutes)),
    }
    return res


def get_minuets_in_period(time_start, time_end):
    minuets = []
    if time_start == time_end:
        return []
    # time_start = time_increase(time_start)
    while time_end > time_start:
        minuets.append(time_start)
        time_start = time_increase(time_start)
    return minuets


def minuets_to_time(minuets):
    return "%s:%s" % (to_2_digits(int(minuets / 60)), to_2_digits(minuets % 60))


def time_increase(time, increase=1):
    x = datetime.strptime(time, "%H:%M") + relativedelta(minutes=increase)
    return x.strftime("%H:%M")

    splitd = time.split(':')
    hour = int(splitd[0])
    minuet = int(splitd[1])
    minuet += increase
    if minuet >= 60:
        minuet = 0
        hour += 1
    hour = to_2_digits(hour)
    minuet = to_2_digits(minuet)
    return "%s:%s" % (hour, minuet)


def to_2_digits(number):
    if len(str(number)) >= 2:
        return str(number)
    else:
        return "0%s" % (str(number))

# over_time_calc(official_workings, actual_workings)
