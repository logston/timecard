#! /usr/bin/env python
import argparse
from datetime import datetime, timedelta
import os
import sys


DATETIME_FORMAT = '%Y%m%dT%H:%M:%S'


def parse_line(line):
    dt, comments = line.split('-')
    dt = datetime.strptime(dt.strip(), DATETIME_FORMAT)
    return dt, comments.strip()


def get_timecard_lines(file_):
    with open(file_) as fp:
        lines = fp.readlines()
    return [parse_line(line) for line in lines]


def count_time(lines, before=None, after=None):
    running_total = 0
    working = False
    last_in_dt = datetime(2015, 1, 1)  # arbitrary dt
    for dt, comments in lines:
        if (after and dt < after) or (before and dt > before):
            continue
        if not working and comments.startswith('in'):
            working = True
            last_in_dt = dt
        elif working and comments.startswith('out'):
            running_total += (dt - last_in_dt).total_seconds()
            working = False
    return running_total, working


def print_work_today(lines):
    now = datetime.utcnow()
    day_start = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if now.hour < 8:
        day_start -= timedelta(day=1)
    seconds, _ = count_time(lines, after=day_start)
    print('Work today (since {} UTC): {:.3} hours'
          ''.format(day_start, seconds / 3600))


def print_work_this_week(lines):
    # get most recent Monday morning
    now = datetime.utcnow()
    monday = now - timedelta(days=now.weekday())
    monday = monday.replace(hour=8, minute=0, second=0, microsecond=0)
    seconds, _ = count_time(lines, after=monday)
    print('Work in past week (since {} UTC): {:.3} hours'
          ''.format(monday, seconds / 3600))


def print_status(lines):
    print('NOW {} (UTC)'.format(datetime.utcnow()))
    is_in = is_checked_in(lines)
    print('Currently CHECKED {}'.format('IN' if is_in else 'OUT'))
    print_work_today(lines)
    print_work_this_week(lines)


def check_in(timecard_file, comment):
    comment = ' '.join(comment)
    dt_string = '{}'.format(datetime.utcnow().strftime(DATETIME_FORMAT))
    with open(timecard_file, 'a') as fp:
        fp.write(dt_string + ' - in ' + comment + '\n')
    sys.stdout.write('CHECKED IN: {}\n'.format(comment))


def check_out(timecard_file, comment):
    comment = ' '.join(comment)
    dt_string = '{}'.format(datetime.utcnow().strftime(DATETIME_FORMAT))
    with open(timecard_file, 'a') as fp:
        fp.write(dt_string + ' - out ' + comment + '\n')
    sys.stdout.write('CHECKED OUT: {}\n'.format(comment))


def is_checked_in(lines):
    _, working = count_time(lines)
    return working


def switch(timecard_file, args):
    lines = get_timecard_lines(timecard_file)

    if args.cmd in ('in', 'out'):
        is_in = is_checked_in(lines)
        if args.cmd == 'in' and not is_in:
            check_in(timecard_file, args.comment)
        elif args.cmd == 'out' and is_in:
            check_out(timecard_file, args.comment)
        else:
            sys.stderr.write('Can not check {0}. You are already checked {0}.\n'
                             ''.format(args.cmd.upper()))
            sys.exit(1)

    elif args.cmd == 'st':
        print_status(lines)

    else:
        sys.stderr.write('Invalid command: {}\n')
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('cmd')
    parser.add_argument('comment', nargs=argparse.REMAINDER)
    args = parser.parse_args()

    timecard_file = os.path.expanduser('~/.timecard/timecard.txt')
    if not timecard_file:
        sys.stderr.write('No timecard file found.\n')
        sys.exit(1)

    switch(timecard_file, args)


if __name__ == '__main__':
    main()

