#!/usr/bin/env python2
"""
A Google Tasks command line interface.
Author: Ajay Roopakalu (https://github.com/jrupac/tasky)

Fork: Conner McDaniel (https://github.com/connermcd/tasky)
        - Website: connermcd.com
        - Email: connermcd using gmail
"""

# TODO:
#  * error catching
#  * make code cleaner/better

from __future__ import print_function

from apiclient.discovery import build
from argparse import ArgumentParser
from collections import OrderedDict
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.file import Storage
from oauth2client.tools import run

import datetime as dt
import httplib2
import os
import shlex
import sys
import time
# import json # TODO

USAGE = """[a]dd, [c]lear, [d]elete, [e]dit, [r]emove task,
[l]ist, [m]ove, [n]ew list/re[n]ame, [t]oggle, [q]uit: """

tasky_dir = os.path.join(os.environ['HOME'], '.tasky')
KEYS_FILE = os.path.join(tasky_dir, 'keys.txt')
service = None
TaskLists = OrderedDict()
IDToTitle = OrderedDict()
UNCHANGED = 0
MODIFIED = 1
DELETED = 2


def add_task(listIndex, task):
    global TaskLists

    tasklist = TaskLists[TaskLists.keys()[listIndex]]
    if 'parent' in task:
        parent = tasklist.keys()[task['parent']]
        newTask = service.tasks().insert(
            tasklist=TaskLists.keys()[listIndex],
            parent=parent,
            body=task
            ).execute()
        # Re-insert the new task in order
        newDict = OrderedDict()
        for tt in tasklist:
            newDict[tt] = tasklist[tt]
            if tt is parent:
                newDict[newTask['id']] = newTask
    else:
        newTask = service.tasks().insert(
            tasklist=TaskLists.keys()[listIndex],
            body=task
            ).execute()
        newDict = OrderedDict()
        newDict[newTask['id']] = newTask
        for tt in tasklist:
            newDict[tt] = tasklist[tt]

    # Update records
    TaskLists[TaskLists.keys()[listIndex]] = newDict
    IDToTitle[newTask['id']] = newTask['title']
    newTask['modified'] = UNCHANGED


def move_task(listIndex, task, args):
    tasklistIndex = TaskLists.keys()[listIndex]
    tasklist = TaskLists[tasklistIndex]
    after = None
    parent = None

    if (args['after'] is not None and
            args['after'] != -1 and
            int(args['after'][0]) != -1):
        after = tasklist.keys()[int(args['after'][0])]

    if args['parent'] is not None:
        parent = tasklist.keys()[int(args['parent'][0])]
    elif 'parent' in task:
        parent = task['parent']

    newTask = service.tasks().move(
        tasklist=tasklistIndex,
        task=task['id'], parent=''.join(parent),
        previous=''.join(after),
        body=task
        ).execute()
    # del TaskLists[tasklistIndex][task['id']]
    # tasklist[newTask['id']] = newTask
    # IDToTitle[newTask['id']] = newTask['title']
    # newTask['modified'] = UNCHANGED


def remove_task(listIndex, task):
    tasklist = TaskLists[TaskLists.keys()[listIndex]]

    # If already deleted, do nothing
    if task['modified'] is DELETED:
        return
    task['modified'] = DELETED
    del IDToTitle[task['id']]

    # Also delete all children of deleted tasks
    for taskID in tasklist:
        t = tasklist[taskID]
        if ('parent' in t and
                t['parent'] in tasklist and
                tasklist[t['parent']]['modified'] is DELETED):
            t['modified'] = DELETED
            if t['id'] in IDToTitle:
                del IDToTitle[t['id']]


def toggle_task(listIndex, task):
    tasklist = TaskLists[TaskLists.keys()[listIndex]]

    if task['modified'] is DELETED:
        return
    task['modified'] = MODIFIED

    if task['status'] == 'needsAction':
        task['status'] = 'completed'
    else:
        task['status'] = 'needsAction'
        if 'completed' in task:
            del task['completed']

    # Also toggle all children whose parents were toggled
    toggle_tree = [task['id']]
    for taskID in tasklist:
        t = tasklist[taskID]
        if t['status'] is DELETED:
            continue
        if 'parent' in t and t['parent'] in toggle_tree:
            t['status'] = tasklist[t['parent']]['status']
            if t['status'] == 'needsAction' and 'completed' in t:
                del t['completed']
            toggle_tree.append(t['id'])
            t['modified'] = MODIFIED
            tasklist[t['id']] = t


def get_data():
    global TaskLists
    # Only retrieve data once per run
    if TaskLists != {}:
        return

    # Fetch task lists
    tasklists = service.tasklists().list().execute()

    # No task lists
    if 'items' not in tasklists:
        return

    # Over all task lists
    for tasklist in tasklists['items']:
        # Handle repeats
        if tasklist['title'] in IDToTitle:
            continue
        IDToTitle[tasklist['id']] = tasklist['title']
        TaskLists[tasklist['id']] = OrderedDict()
        tasks = service.tasks().list(tasklist=tasklist['id']).execute()
        # No task in current list
        if 'items' not in tasks:
            continue
        # Over all tasks in a given list
        for task in tasks['items']:
            IDToTitle[task['id']] = task['title']
            # Set everything to be initially unmodified
            task['modified'] = UNCHANGED
            TaskLists[tasklist['id']][task['id']] = task


def put_data():
    # Nothing to write home about
    if TaskLists == {}:
        return

    for tasklistID in TaskLists:
        for taskID in TaskLists[tasklistID]:
            task = TaskLists[tasklistID][taskID]
            if task['modified'] is UNCHANGED:
                continue
            elif task['modified'] is MODIFIED:
                service.tasks().update(
                    tasklist=tasklistID,
                    task=taskID,
                    body=task
                    ).execute()
            elif task['modified'] is DELETED:
                service.tasks().delete(
                    tasklist=tasklistID,
                    task=taskID
                    ).execute()


def print_all_tasks(tasklistID):
    tab = '  '

    # No task lists
    if TaskLists == {}:
        print('Found no task lists.')
        return

    # print(json.dumps(TaskLists, indent=4)) TODO

    # Use a dictionary to store the indent depth of each task
    depthMap = {tasklistID: 0}
    depth = 1

    # Print task name
    if len(TaskLists[tasklistID]) == 0:
        print(textcolor.HEADER + IDToTitle[tasklistID] +  textcolor.ENDC, '(empty)')
        #sys.exit(False)
    else:
        print(textcolor.HEADER + IDToTitle[tasklistID] + textcolor.ENDC)

    for taskID in TaskLists[tasklistID]:
        task = TaskLists[tasklistID][taskID]
        if task['modified'] is DELETED:
            continue
        depth = 1
        isCompleted = (task['status'] == 'completed')

        # Set the depth of the current task
        if 'parent' in task and task['parent'] in depthMap:
            depth = depthMap[task['parent']] + 1
        depthMap[task['id']] = depth

        # Print x in box if task has already been completed
        if isCompleted:
            print(tab * depth,
                  TaskLists[tasklistID].keys().index(taskID),
                  '[x]',
                  task['title'])
                # task['position'], # TODO
        else:
            print(textcolor.TITLE + tab * depth,
                  TaskLists[tasklistID].keys().index(taskID),
                  '[ ]',
                  task['title'] + textcolor.ENDC)
                # task['position'] # TODO

        # Print due date if specified
        if 'due' in task:
            date = dt.datetime.strptime(task['due'],
                                        '%Y-%m-%dT%H:%M:%S.%fZ')
            output = date.strftime('%a, %b %d, %Y')
            print(tab * (depth + 1), textcolor.DATE +
                  'Due Date: {0}'.format(output) + textcolor.ENDC)

        # Print notes if specified
        if 'notes' in task:
            print(tab * (depth + 1), textcolor.NOTES +
                  'Notes: {0}'.format(task['notes']) + textcolor.ENDC)


def print_summary():
    for tasklistID in TaskLists:
        print(TaskLists.keys().index(tasklistID),
              IDToTitle[tasklistID],
              '(', len(TaskLists[tasklistID]), ')')


def handle_input_args(args, atasklistID=0):
    action = ''.join(args['action'])
    args['list'] = int(args['list'])
    if atasklistID == 0:
        atasklistID = args['list']
    tasklistID = TaskLists.keys()[atasklistID]
    tasklist = TaskLists[tasklistID]

    if action is 'a':
        for title in args['title']:
            task = {'title': ''.join(title)}
            if args['date'] is not None:
                dstr = ''.join(args['date'])
                d = time.strptime(dstr, "%m/%d/%Y")
                task['due'] = (str(d.tm_year) + '-' +
                               str(d.tm_mon) + '-' +
                               str(d.tm_mday) +
                               'T12:00:00.000Z')
            if args['note'] is not None:
                task['notes'] = ''.join(args['note'])
            if args['parent'] is not None:
                task['parent'] = int(args['parent'][0])
            print('Adding task...')
            add_task(atasklistID, task)
    if action is 'd':
        readIn = raw_input('This will delete the list "' +
                           IDToTitle[tasklistID] +
                           '" and all its contents permanently. Are you sure? (y/n) ')
        if readIn is 'Y' or readIn is 'y':
            service.tasklists().delete(tasklist=tasklistID).execute()
        del TaskLists[tasklistID]
        print_summary()
        put_data()
        sys.exit(True)
    if action is 'n':
        if args['rename'] is True:
            print('Renaming task list...')
            tasklist = service.tasklists().get(tasklist=tasklistID).execute()
            tasklist['title'] = args['title'][0]
            IDToTitle[tasklistID] = args['title'][0]
            service.tasklists().update(
                tasklist=tasklistID,
                body=tasklist
                ).execute()
            time.sleep(3)
        else:
            print('Creating new task list...')
            newTaskList = service.tasklists().insert(
                body={'title': args['title']}
                ).execute()
            IDToTitle[newTaskList['id']] = newTaskList['title']
            TaskLists[newTaskList['id']] = OrderedDict()
        print_summary()
        put_data()
        sys.exit(True)
    #elif tasklist == {}:
        #print(IDToTitle[tasklistID], '(empty)')
        #return
    elif action is 'e':
        print('Editing task...')
        task = tasklist[tasklist.keys()[int(args['index'][0])]]
        if args['title'] is not None:
            task['title'] = ''.join(args['title'])
        if args['date'] is not None:
            dstr = ''.join(args['date'])
            d = time.strptime(dstr, "%m/%d/%Y")
            task['due'] = (str(d.tm_year) + '-' +
                           str(d.tm_mon) + '-' +
                           str(d.tm_mday) +
                           'T12:00:00.000Z')
        if args['note'] is not None:
            task['notes'] = ''.join(args['note'])
        if task['modified'] == DELETED:
            return
        task['modified'] = MODIFIED
    elif action is 'm':
        print('Moving task...')
        task = tasklist[tasklist.keys()[int(args['index'][0])]]
        move_task(atasklistID, task, args)
        put_data()
        sys.exit(True)
    elif action is 'c':
        if args['all'] is True:
            print('Removing all tasks...')
            for taskID in tasklist:
                remove_task(atasklistID, tasklist[taskID])
        else:
            print('Clearing completed tasks...')
            service.tasks().clear(tasklist=tasklistID).execute()
            for taskID in tasklist:
                task = tasklist[taskID]
                if task['status'] == 'completed':
                    task['modified'] = DELETED
    elif action is 'r':
        print('Removing task...')
        for index in args['index']:
            index = int(index)
            remove_task(atasklistID, tasklist[tasklist.keys()[index]])
    elif action is 't':
        print('Toggling task...')
        for index in args['index']:
            index = int(index)
            toggle_task(atasklistID, tasklist[tasklist.keys()[index]])

    if action is 'l' and args['all'] is True:
        for tasklistID in TaskLists:
            print_all_tasks(tasklistID)
    elif action is 'l' and args['summary'] is True:
        print_summary()
    elif action is 'i':
        readLoop(args, atasklistID)
    else:
        print_all_tasks(tasklistID)


def parse_arguments(args):
    parser = ArgumentParser(description="""A Google Tasks Client.
    Type tasky <argument> -h for more detailed information.""")

    # Parse arguments
    if len(args) > 1:
        subparsers = parser.add_subparsers(dest='action')
        parser.add_argument('-l', '--list',
                            default=0,
                            help='Specifies task list (default: 0)')

        parser_a = subparsers.add_parser('a')
        parser_a.add_argument('title', nargs='*',
                              help='The name of the task.')
        parser_a.add_argument('-d', '--date', nargs=1,
                              help='A date in MM/DD/YYYY format.')
        parser_a.add_argument('-n', '--note', nargs=1,
                              help='Any quotation-enclosed string.')
        parser_a.add_argument('-p', '--parent', nargs=1,
                              help='The id of the parent task.')

        parser_e = subparsers.add_parser('e')
        parser_e.add_argument('index', nargs=1,
                              help='Index of the task to edit.')
        parser_e.add_argument('-t', '--title', nargs=1,
                              help='The new title after editing.')
        parser_e.add_argument('-d', '--date', nargs=1,
                              help='A new date in MM/DD/YYYY format.')
        parser_e.add_argument('-n', '--note', nargs=1,
                              help='The new note after editing.')

        parser_m = subparsers.add_parser('m')
        parser_m.add_argument('index', nargs=1,
                              help='Index of the task to move.')
        parser_m.add_argument('-a', '--after',
                              nargs=1, default=-1,
                              help='Move the task after this index. (default: -1)')
        parser_m.add_argument('-p', '--parent',
                              nargs=1,
                              help='Make the task a child of this index.')

        parser_c = subparsers.add_parser('c')
        parser_c.add_argument('-a', '--all',
                              action='store_true',
                              help='Remove all tasks, completed or not.')

        subparsers.add_parser('d')
        subparsers.add_parser('i')

        parser_n = subparsers.add_parser('n')
        parser_n.add_argument('title', nargs='*',
                              help='The name of the new task list.')
        parser_n.add_argument('-r', '--rename', action='store_true',
                              help='Set if renaming an already existing task list.')

        parser_l = subparsers.add_parser('l')
        parser_l.add_argument('-a', '--all', action='store_true',
                              help='Print all tasks in all task lists.')
        parser_l.add_argument('-s', '--summary', action='store_true',
                              help='Print a summary of available task lists.')

        parser_r = subparsers.add_parser('r')
        parser_r.add_argument('index', nargs='*',
                              help='Index of the task to remove.')

        parser_t = subparsers.add_parser('t')
        parser_t.add_argument('index', nargs='*',
                              help='Index of the task to toggle.')
    sys.argv = args
    return vars(parser.parse_args())


class Auth():

    def __init__(self, key_file):
        try:
            with open(key_file, 'r') as self.f:
                self.clientid = self.f.readline()
                self.clientsecret = self.f.readline()
                self.apikey = self.f.readline()
        except IOError:
            self.clientid = raw_input("Enter your clientID: ")
            self.clientsecret = raw_input("Enter your client secret: ")
            self.apikey = raw_input("Enter your API key: ")
            self.write_auth()

    def write_auth(self):
        if not os.path.exists(tasky_dir):
            os.makedirs(tasky_dir)
        with open(KEYS_FILE, 'w') as self.auth:
            self.auth.write(str(self.clientid) + '\n')
            self.auth.write(str(self.clientsecret) + '\n')
            self.auth.write(str(self.apikey) + '\n')

    def get_client_ID(self):
        return self.clientid

    def get_client_secret(self):
        return self.clientsecret

    def get_API_key(self):
        return self.apikey


def authenticate():
    global service
    f = Auth(KEYS_FILE)

    # OAuth 2.0 Authentication
    FLOW = OAuth2WebServerFlow(
        client_id=f.get_client_ID(),
        client_secret=f.get_client_secret(),
        scope='https://www.googleapis.com/auth/tasks',
        user_agent='Tasky/v1')

    # If credentials don't exist or are invalid, run through the native client
    # flow. The Storage object will ensure that if successful the good
    # Credentials will get written back to a file.
    storage = Storage(os.path.join(tasky_dir, 'tasks.dat'))
    credentials = storage.get()

    if credentials is None or credentials.invalid:
        credentials = run(FLOW, storage)

    http = httplib2.Http()
    http = credentials.authorize(http)

    # The main Tasks API object
    service = build(serviceName='tasks', version='v1', http=http,
                    developerKey=f.get_API_key())


def readLoop(args, tasklistID=0):
    while True:
        readIn = raw_input(USAGE)
        if readIn is '' or readIn is 'q':
            break
        args = shlex.split(readIn)
        args[:0] = '/'
        args = parse_arguments(args)
        handle_input_args(args, tasklistID)


def main(args):
    get_data()

    if len(args) > 1:
        handle_input_args(args)
    else:
        readLoop(args)
    put_data()
    sys.exit(True)

class textcolor:
    # Colored output
    # It is possible to use more conventional colors:
    # i.e. HEADER = '\033[1;31m'
    HEADER = '\033[1;38;5;218m'
    DATE = '\033[1;38;5;249m'
    NOTES = '\033[1;38;5;252m'
    TITLE = '\033[1;38;5;195m'
    ENDC = '\033[0m'

    def disable(self):
        self.HEADER = ''
        self.DATE = ''
        self.NOTES = ''
        self.ENDC = ''    

if __name__ == '__main__':
    authenticate()
    main(parse_arguments(sys.argv))
