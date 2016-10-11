#! /usr/bin/env python
import argparse
import csv
from datetime import datetime, timedelta
import os
import sys


class TimeCardManager(object):
    DATETIME_FORMAT = '%Y%m%dT%H:%M:%S'

    OP_IN = 'IN'
    OP_OUT = 'OUT'
    OP_ADD = 'ADD'
    OP_SUB = 'SUB'
    OP_STATUS = 'ST'
    IN_OUT_OPS = frozenset((OP_IN, OP_OUT))
    ADD_SUB_OPS = frozenset((OP_ADD, OP_SUB))
    VALID_OPS = frozenset((OP_IN, OP_OUT, OP_ADD, OP_SUB, OP_STATUS))

    def __init__(self, data_file):
        self.data_file = data_file
        self.op_rows = []
        self.last_in_out_op = None
        self.now = datetime.utcnow()

    def handle_op(self, op, value):
        # read file
        self.read_data_file()

        # validate op
        op = op.upper()
        self.validate_op(op)

        # validate value
        self.validate_value(op, value)

        # add op + save file if necessary
        if op in self.IN_OUT_OPS:
            value = datetime.utcnow().strftime(self.DATETIME_FORMAT)
            self.save_op(op, value)
            self.last_in_out_op = op

        elif op in self.ADD_SUB_OPS:
            self.save_op(op, value)

        # print status
        self.print_status()

    def read_data_file(self):
        with open(self.data_file) as fp:
            reader = csv.reader(fp)
            self.op_rows = list(reader)

    def validate_op(self, op):
        if op not in self.VALID_OPS:
            raise ValueError('Invalid op code: {}'.format(op))

        for row_op, row_value in reversed(self.op_rows):
            if row_op in self.IN_OUT_OPS:
                self.last_in_out_op = row_op
                break
        else:
            # time card has never been used. act like we are checked out
            self.last_in_out_op = self.OP_OUT

        if not self.last_in_out_op:
            raise ValueError('No IN/OUT op code in time card data file.')

        if self.last_in_out_op == op:
            msg = 'Can not check {0}. You are already checked {0}'
            raise ValueError(msg.format(op))

        if self.last_in_out_op == self.OP_IN and op in self.ADD_SUB_OPS:
            raise ValueError('Can not add/sub time while checked in.')

    def validate_value(self, op, value):
        if op in self.ADD_SUB_OPS:
            try:
                int(value)
            except (TypeError, ValueError):
                msg = 'Can not {} {} to given time card'
                raise ValueError(msg.format(op, value))

    def save_op(self, op, value):
        row = (op, value)
        with open(self.data_file, 'a') as fp:
            writer = csv.writer(fp)
            writer.writerow(row)
        self.op_rows.append(row)

    def print_status(self):
        print('You are currently CHECKED {}'.format(self.last_in_out_op))
        print('NOW {} (UTC)'.format(self.now))
        self.print_work_today()
        self.print_work_this_week()
        self.print_work_last_week()

    def print_work_today(self):
        day_start = self.now.replace(hour=8, minute=0, second=0, microsecond=0)
        if self.now.hour < 8:
            day_start -= timedelta(days=1)
        seconds = self.count_time(day_start)

        msg = 'Work today (since {} UTC): {:.3} hours'
        msg = msg.format(day_start, seconds / 3600.0)
        print(msg)

    def print_work_last_week(self):
        # get most recent Monday morning
        monday = self.now - timedelta(days=self.now.weekday())
        monday = monday.replace(hour=8, minute=0, second=0, microsecond=0)
        last_week_monday = monday - timedelta(days=7)
        seconds = self.count_time(last_week_monday, monday)

        msg = 'Work last week ({} - {} UTC): {:.3} hours'
        msg = msg.format(last_week_monday, monday, seconds / 3600.0)
        print(msg)

    def print_work_this_week(self):
        # get most recent Monday morning
        monday = self.now - timedelta(days=self.now.weekday())
        monday = monday.replace(hour=8, minute=0, second=0, microsecond=0)
        seconds = self.count_time(monday)

        msg = 'Work this week (since {} UTC): {:.3} hours'
        msg = msg.format(monday, seconds / 3600.0)
        print(msg)

    def count_time(self, start_ts=None, end_ts=None):
        running_total = 0
        last_in_dt = datetime(2015, 1, 1)  # arbitrary dt
        checked_in = False

        for row_op, row_value in self.op_rows:
            if row_op in self.IN_OUT_OPS:
                row_value = datetime.strptime(row_value, self.DATETIME_FORMAT)
            elif row_op in self.ADD_SUB_OPS:
                row_value = timedelta(minutes=int(row_value))

            if row_op in self.IN_OUT_OPS:
                if (start_ts and row_value < start_ts) or (end_ts and row_value > end_ts):
                    continue

            if not checked_in and row_op == self.OP_IN:
                checked_in = True
                last_in_dt = row_value

            elif checked_in and row_op == self.OP_OUT:
                running_total += (row_value - last_in_dt).total_seconds()
                checked_in = False

            elif (not checked_in and 
                  row_op in self.ADD_SUB_OPS and
                  # use the last_in_dt to determine if ADD / SUB op should be
                  # counted for this interval
                  (start_ts and last_in_dt > start_ts) and
                  (end_ts and last_in_dt < end_ts)):
                if row_op == self.OP_ADD:
                    running_total += row_value.total_seconds()
                else:
                    running_total -= row_value.total_seconds()

        if checked_in and not end_ts:
            running_total += (self.now - last_in_dt).total_seconds()

        return running_total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('op')
    parser.add_argument('value', nargs=argparse.REMAINDER)
    args = parser.parse_args()

    value = args.value[0] if args.value else None

    manager = TimeCardManager(os.path.expanduser('~/.timecard/data.csv'))
    manager.handle_op(args.op, value)


if __name__ == '__main__':
    main()

