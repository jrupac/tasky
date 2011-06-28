#!/usr/bin/env python

from apiclient.discovery import build
from apiclient.oauth import OAuthCredentials
from oauth2client.file import Storage
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.tools import run
from string import find
from collections import OrderedDict
from argparse import ArgumentParser
from operator import itemgetter

import httplib2
import sys
import datetime as dt
import time
import os
import readline
import keys

parser = None
arguments = False

# Parse arguments
if len(sys.argv) > 1:
    arguments = True
    parser = ArgumentParser(description = "A Google Tasks Client.")
    subparsers = parser.add_subparsers(dest = 'action')

    parser_a = subparsers.add_parser('a')
    parser_a.add_argument('-l', '--list', action = 'store_true', \
    default = False, help = 'If given, the updated lists will be printed\
    after execution')
    parser_a.add_argument('-t', '--title', nargs = 1, required = True, \
    help = 'This non-optional argument specifies the name of the task.')
    parser_a.add_argument('-d', '--date', nargs = 1, \
    help = 'This optional argument must of the of the form MM/DD/YYYY.')
    parser_a.add_argument('-n', '--note', nargs = 1, \
    help = 'This optional argument can be any quotation-enclosed string.')
    parser_a.add_argument('-p', '--parent', nargs = 1, \
    help = 'This optional argument specifies the name of the task.')

    parser_r = subparsers.add_parser('r')
    parser_r.add_argument('-l', '--list', action = 'store_true', \
    default = False, help = 'If given, the updated lists will be printed\
    after execution')
    parser_r.add_argument('-t', '--title', nargs = 1, required = True, \
    help = 'This non-optional argument specifies the name of the task.')

    parser_l = subparsers.add_parser('l')

    parser_t = subparsers.add_parser('t')
    parser_t.add_argument('-l', '--list', action = 'store_true', \
    default = False, help = 'If given, the updated lists will be printed\
    after execution')
    parser_t.add_argument('-t', '--title', nargs = 1, required = True, \
    help = 'This non-optional argument specifies the name of the task.')

    sys.argv = vars(parser.parse_args())

print 'Verifying authentication...'
f = keys.Auth('keys.txt')

# OAuth 2.0 Authentication
FLOW = OAuth2WebServerFlow(
    client_id=f.get_client_ID(),
    client_secret=f.get_client_secret(),
    scope='https://www.googleapis.com/auth/tasks',
    user_agent='Tasky/v1')

# If the Credentials don't exist or are invalid, run through the native client
# flow. The Storage object will ensure that if successful the good
# Credentials will get written back to a file.
storage = Storage('tasks.dat')
credentials = storage.get()

if credentials is None or credentials.invalid:
  credentials = run(FLOW, storage)

http = httplib2.Http()
http = credentials.authorize(http)

# The main Tasks API object
service = build(serviceName='tasks', version='v1', http=http, 
                developerKey=f.get_API_key())

TaskLists = {}
IDToTitle = {}
TaskNames = []
UNCHANGED = 0
UPDATED = 1
DELETED = 2
bold = lambda x : '\x1b[1m' + x + '\x1b[0m'
strike = lambda x : '\x1b[9m' + x + '\x1b[0m'

class Completer():
    def __init__(self):
        self.matches = []
        self.completions = []
        self.DEBUG = False
     
    def complete_task_names(self, text, state):
        self.completions = TaskNames
        response = None
       
        if state is 0:
            if text:
                self.matches = [s for s in self.completions 
                                if s and s.startswith(text)]
            else:
                self.matches = self.completions[:]

        try:
            response = self.matches[state]
        except IndexError:
            pass
        
        return response
    
    def complete_none(self, text, state):
        return None

def search_task(substr):
    length = len(substr)
    matches = {}
    i = 1

    for tasklistID in TaskLists:
        for taskID in TaskLists[tasklistID]:
            task = TaskLists[tasklistID][taskID]
            if task['modified'] is DELETED:
                continue
            index = task['title'].find(substr)
            if index != -1:
                matches[i] = (tasklistID, task, index)
                i += 1

    # No matches
    if i is 1:
        return None
    # Unique match
    elif i is 2:
        return matches[i-1][:2]
    # Multiple matches
    else:
        # Print all matches
        for ii in xrange(1, i):
            (listID, task, index) = matches[ii]
            title = task['title']
            print '({0}): {1} : {2}{3}{4}'.format(ii, IDToTitle[listID], title[:index], \
                    bold(substr), title[index + length:]) 
        while True:
            choice = raw_input('Multiple matches found. Enter number of your choice: ')
            try:
                return matches[int(choice)][:2]
            except:
                print 'Invalid input. Please try again.'

def add_task(taskInfo):
    matches = {}
    i = 1
    choice = 1
    (listID, task) = taskInfo
    
    if listID is not None:
        matches[choice] = listID
    else:
        for tasklistID in TaskLists:
            matches[i] = tasklistID
            i += 1

        # No task lists found - report error
        if i is 1:
            print 'No task lists found.'
            return
        
        # In case of multiple lists, decide which one
        if i > 2:
            for ii in xrange(1, i):
                print '({0}): {1}'.format(ii, IDToTitle[matches[ii]]) 
            while True:
                try:
                    choice = int(raw_input('Multiple lists found. Enter number of your choice: '))
                    # Check if input is a valid choice
                    dic = TaskLists[matches[choice]]
                    break
                except:
                    print 'Invalid input. Please try again.'

    dic = TaskLists[matches[choice]]
    newTask = None

    if 'parent' in task:
        newTask = service.tasks().insert(tasklist = matches[choice], \
                parent = task['parent'], body = task).execute()
        # Re-insert the new task in order
        newDict = OrderedDict()
        for tt in dic:
            newDict[tt] = TaskLists[matches[choice]][tt]
            if tt is task['parent']:
                newDict[newTask['id']] = newTask
        TaskLists[matches[choice]] = newDict
    else:
        newTask = service.tasks().insert(tasklist = matches[choice], body = task).execute()
        TaskLists[matches[choice]][newTask['id']] = newTask

    # Update records
    IDToTitle[newTask['id']] = newTask['title']
    TaskNames.append(newTask['title'])
    newTask['modified'] = UNCHANGED

def remove_task(taskInfo):
    global TaskLists
    (listID, task) = taskInfo

    # If already deleted, do nothing
    if task['modified'] is DELETED:
        return

    # Delete the given task
    task['modified'] = DELETED
    # Tidy up
    del IDToTitle[task['id']]
    TaskNames.remove(task['title'])
    
    # Also delete all children of deleted tasks
    for taskID in TaskLists[listID]:
        t = TaskLists[listID][taskID]
        if 'parent' in t and TaskLists[listID][t['parent']]['modified'] is DELETED:
            t['modified'] = DELETED
            if t['id'] in IDToTitle:
                del IDToTitle[t['id']]
                TaskNames.remove(t['title'])

def toggle_task(taskInfo):
    global TaskLists
    (listID, task) = taskInfo

    # If already deleted, do nothing
    if task['modified'] is DELETED:
        return

    # toggle_task the given task
    task['modified'] = UPDATED
    if task['status'] == 'needsAction':
        task['status'] = 'completed'
    else:
        task['status'] = 'needsAction'
        if 'completed' in task:
            del task['completed']

    # Write back changes locally
    TaskLists[listID][task['id']] = task    
    prevs = [task['id']]

    # Also toggle all children who parents were toggled
    for taskID in TaskLists[listID]:
        t = TaskLists[listID][taskID]
        if t['status'] is DELETED:
            continue
        if 'parent' in t and t['parent'] in prevs:
            t['status'] = TaskLists[listID][t['parent']]['status']
            if t['status'] == 'needsAction' and 'completed' in t:
                del t['completed']
            prevs.append(t['id'])
            t['modified'] = UPDATED
            TaskLists[listID][t['id']] = t

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
        IDToTitle[tasklist['id']] = tasklist['title']
        TaskLists[tasklist['id']] = OrderedDict()
        tasks = service.tasks().list(tasklist = tasklist['id']).execute()
        # No task in current list
        if 'items' not in tasks:
            continue
        # Over all tasks in a given list
        for task in tasks['items']:
            TaskNames.append(task['title'])
            IDToTitle[task['id']] = task['title']
            # Set everything to be initially unmodified
            task['modified'] = UNCHANGED
            TaskLists[tasklist['id']][task['id']] = task

def put_data():
    global TaskLists

    # Nothing to write home about
    if TaskLists == {}:
        return

    for tasklistID in TaskLists:
        for taskID in TaskLists[tasklistID]:
            task = TaskLists[tasklistID][taskID]
            if task['modified'] is UNCHANGED:
                continue
            elif task['modified'] is UPDATED:
                service.tasks().update(tasklist = tasklistID, task = taskID, body = task).execute()
            elif task['modified'] is DELETED:
                service.tasks().delete(tasklist = tasklistID, task = taskID).execute()

def print_all_tasks():
    global TaskLists
    arrow = u'\u2192'
    tab = '  '

    # No task lists
    if TaskLists is {}:
        print 'Found no task lists.'
        return

    numLists = len(TaskLists)
    print 'Found {0} task list(s):'.format(numLists)

    for tasklistID in TaskLists:
        # Use a dictionary to store the indent depth of each task
        depthMap = { tasklistID : 0 }
        depth = 1

        # Print task name
        print tab * depth, IDToTitle[tasklistID]
        
        # No tasks
        if TaskLists[tasklistID] is {}:
            continue

        for taskID in TaskLists[tasklistID]:
            task = TaskLists[tasklistID][taskID]
            if task['modified'] is DELETED:
                continue
            depth = 2
            isCompleted = (task['status'] == 'completed')
            
            # Set the depth of the current task
            if 'parent' in task and task['parent'] in depthMap:
                depth = depthMap[task['parent']] + 1
            depthMap[task['id']] = depth

            # Print strike-through if task has already been completed
            if isCompleted:
                print tab * depth, u'\u2611', strike(bold(task['title']))
            else:
                print tab * depth, u'\u2610', bold(task['title'])

            # Print due date if specified
            if 'due' in task:
                date = dt.datetime.strptime(task['due'], '%Y-%m-%dT%H:%M:%S.%fZ')
                output = date.strftime('%a, %b %d, %Y')
                if isCompleted:
                    print tab * (depth + 1), arrow, strike('Due Date: {0}'.format(output))
                else:
                    print tab * (depth + 1), arrow, 'Due Date: {0}'.format(output)

            # Print notes if specified
            if 'notes' in task:
                if isCompleted:
                    print tab * (depth + 1), arrow, strike('Notes: {0}'.format(task['notes']))
                else:
                    print tab * (depth + 1), arrow, 'Notes: {0}'.format(task['notes'])

def handle_input_args(argv):
    action = ''.join(argv['action'])
    
    if action is 'l':
        print_all_tasks()
        return
    elif action is 'a':
        task = { 'title' : ''.join(argv['title']) }
        if argv['date'] is not None:
            dstr = ''.join(argv['date'])
            d = time.strptime(dstr, "%m/%d/%y")
            task['due'] = str(d.tm_year) + '-' + str(d.tm_mon) + '-' + \
            str(d.tm_mday) + 'T12:00:00.000Z'
        if argv['note'] is not None:
            task['notes'] = ''.join(argv['note'])
        if argv['parent'] is not None:
            ret = search_task(''.join(argv['parent']))
            if ret is None:
                print 'No matches found for parent.'
            else:
                (listID, parentTask) = ret
                task['parent'] = parentTask['id']
                print 'Adding task...'
                add_task((listID, task))
                return
        print 'Adding task...'
        add_task((None, task))
    elif action is 'r':
        ret = search_task(''.join(argv['title']))
        if ret is None:
            print 'No match found.'
        else:
            print 'Removing task...'
            remove_task(ret)
    elif action is 't':
        ret = search_task(''.join(argv['title']))
        if ret is None:
            print 'No match found.'
        else:
            print 'Toggling task...'
            toggle_task(ret)
    
    if argv['list'] is True:
        print_all_tasks()

def handle_input(c):
    completer = Completer()
    c_name = completer.complete_task_names
    c_none = completer.complete_none
    readline.set_completer(c_none)

    if c is 'a':
        t = dt.date.today()

        title = raw_input("Name of task: ")
        while title is '':
            print 'Please enter name for task.'
            title = raw_input("Name of task: ")
            
        task = { 'title' : title }
        month = raw_input("Month [MM]: ")
        day = raw_input("Day [DD]): ")
        year = raw_input("Year [YYYY]: ")

        if not (day is '' and month is '' and year is ''):
            if day is '' or not day.isdigit():
                day = t.day
            if month is '' or not month.isdigit():
                month = t.month
            if year is '' or not year.isdigit():
                year = t.year
            task['due'] = str(year) + '-' + str(month) + '-' + str(day) + 'T12:00:00.000Z'

        notes = raw_input("Notes: ")
        if notes is not '':
            task['notes'] = notes
    
        readline.set_completer(c_name)
        parent = raw_input("Name of parent task: ")

        if parent is not '':
            ret = search_task(parent)
            if ret is None:
                print 'No matches found for parent.'
            else:
                (listID, parentTask) = ret
                task['parent'] = parentTask['id']
                print 'Adding task...'
                add_task((listID, task))
                return
        print 'Adding task...'
        add_task((None, task))
    elif c is 'l':
        print_all_tasks()
    elif c is 'r':
        readline.set_completer(c_name)
        substr = raw_input("Name of task: ")
        ret = search_task(substr)
        if ret is None:
            print 'No match found.'
        else:
            print 'Removing task...'
            remove_task(ret)
    elif c is 't':
        readline.set_completer(c_name)
        substr = raw_input("Name of task: ")
        ret = search_task(substr)
        if ret is None:
            print 'No match found.'
        else:
            print 'Toggling task...'
            toggle_task(ret)

def main(argv):
    print 'Retrieving task lists...'
    get_data()

    if arguments:
        handle_input_args(argv)
    else:
        readline.parse_and_bind('tab: complete')
        readline.set_completer_delims(readline.get_completer_delims()[1:])
        print_all_tasks()
        while True:
            readIn = raw_input('[a]dd, [r]emove, [l]ist, [t]oggle, [q]uit: ')
            if readIn is '' or readIn is 'q':
                break
            handle_input(readIn)

    print 'Sending changes...'
    put_data()

if __name__ == '__main__':
    main(sys.argv)
