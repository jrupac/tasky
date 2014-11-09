#!/usr/bin/env python2

"""
A Google Tasks command line interface.
"""

__author__ = 'Ajay Roopakalu (https://github.com/jrupac/tasky)'

# TODO:
#  * error catching

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

USAGE = """
[a]dd, [c]lear, [d]elete, [e]dit, [r]emove task, [l]ist, [m]ove,
[n]ew list/re[n]ame, [t]oggle, [q]uit: """

# Environment constants
TASKY_DIR = os.path.join(os.environ['HOME'], '.tasky')
KEYS_FILE = os.path.join(TASKY_DIR, 'keys.txt')


def ParseArguments(args):
  parser = ArgumentParser(description=(
    'A Google Tasks Client.',
    'Type tasky <argument> -h for more detailed information.'))

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


class TextColor(object):
  """A class to provide terminal keycodes for colored output."""

  HEADER = '\033[1;38;5;218m'
  DATE = '\033[1;38;5;249m'
  NOTES = '\033[1;38;5;252m'
  TITLE = '\033[1;38;5;195m'
  ENDC = '\033[0m'

  def Disable(self):
    self.HEADER = ''
    self.DATE = ''
    self.NOTES = ''
    self.ENDC = ''


class Auth(object):
  """A class to handle persistence and access of various OAuth keys."""

  def __init__(self, keyFile):
    try:
      with open(keyFile, 'r') as self.f:
        self.clientId = self.f.readline()
        self.clientSecret = self.f.readline()
        self.apiKey = self.f.readline()
    except IOError:
      self.clientId = raw_input("Enter your clientID: ")
      self.clientSecret = raw_input("Enter your client secret: ")
      self.apiKey = raw_input("Enter your API key: ")
      self.WriteAuth()

  def WriteAuth(self):
    if not os.path.exists(TASKY_DIR):
      os.makedirs(TASKY_DIR)
    with open(KEYS_FILE, 'w') as self.auth:
      self.auth.write(str(self.clientId) + '\n')
      self.auth.write(str(self.clientSecret) + '\n')
      self.auth.write(str(self.apiKey) + '\n')

  def GetClientId(self):
    return self.clientId

  def GetClientSecret(self):
    return self.clientSecret

  def GetApiKey(self):
    return self.apiKey


class Tasky(object):
  """Main class that handles task manipulation."""

  UNCHANGED = 0
  MODIFIED = 1
  DELETED = 2

  def __init__(self):
    self.taskLists = OrderedDict()
    self.idToTitle = OrderedDict()
    self.Authenticate()
    self.GetData()

  def AddTask(self, listIndex, task):
    tasklist = self.taskLists[self.taskLists.keys()[listIndex]]

    if 'parent' in task:
      parent = tasklist.keys()[task['parent']]
      newTask = self.service.tasks().insert(
          tasklist=self.taskLists.keys()[listIndex], parent=parent,
          body=task).execute()
      # Re-insert the new task in order
      newDict = OrderedDict()
      for tt in tasklist:
        newDict[tt] = tasklist[tt]
        if tt is parent:
          newDict[newTask['id']] = newTask
    else:
      newTask = self.service.tasks().insert(
          tasklist=self.taskLists.keys()[listIndex], body=task).execute()
      newDict = OrderedDict()
      newDict[newTask['id']] = newTask
      for tt in tasklist:
        newDict[tt] = tasklist[tt]

    # Update records
    self.taskLists[self.taskLists.keys()[listIndex]] = newDict
    self.idToTitle[newTask['id']] = newTask['title']
    newTask['modified'] = Tasky.UNCHANGED

  def MoveTask(self, listIndex, task, args):
    tasklistIndex = self.taskLists.keys()[listIndex]
    tasklist = self.taskLists[tasklistIndex]
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

    newTask = self.service.tasks().move(
      tasklist=tasklistIndex, task=task['id'], parent=''.join(parent),
      previous=''.join(after), body=task).execute()
    # del TaskLists[tasklistIndex][task['id']]
    # tasklist[newTask['id']] = newTask
    # IDToTitle[newTask['id']] = newTask['title']
    # newTask['modified'] = UNCHANGED

  def RemoveTask(self, listIndex, task):
    tasklist = self.taskLists[self.taskLists.keys()[listIndex]]

    # If already deleted, do nothing
    if task['modified'] is Tasky.DELETED:
      return
    task['modified'] = Tasky.DELETED
    del self.idToTitle[task['id']]

    # Also delete all children of deleted tasks
    for taskID in tasklist:
      t = tasklist[taskID]
      if ('parent' in t and
          t['parent'] in tasklist and
          tasklist[t['parent']]['modified'] is Tasky.DELETED):
        t['modified'] = Tasky.DELETED
        if t['id'] in self.idToTitle:
          del self.idToTitle[t['id']]

  def ToggleTask(self, listIndex, task):
    tasklist = self.taskLists[self.taskLists.keys()[listIndex]]

    if task['modified'] is Tasky.DELETED:
      return
    task['modified'] = Tasky.MODIFIED

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
      if t['status'] is Tasky.DELETED:
        continue
      if 'parent' in t and t['parent'] in toggle_tree:
        t['status'] = tasklist[t['parent']]['status']
        if t['status'] == 'needsAction' and 'completed' in t:
          del t['completed']
        toggle_tree.append(t['id'])
        t['modified'] = Tasky.MODIFIED
        tasklist[t['id']] = t

  def GetData(self):
    # Only retrieve data once per run
    if self.taskLists != {}:
      return

    # Fetch task lists
    tasklists = self.service.tasklists().list().execute()

    # No task lists
    if 'items' not in tasklists:
      return

    # Over all task lists
    for tasklist in tasklists['items']:
      # Handle repeats
      if tasklist['title'] in self.idToTitle:
        continue
      self.idToTitle[tasklist['id']] = tasklist['title']
      self.taskLists[tasklist['id']] = OrderedDict()
      tasks = self.service.tasks().list(tasklist=tasklist['id']).execute()
      # No task in current list
      if 'items' not in tasks:
        continue
      # Over all tasks in a given list
      for task in tasks['items']:
        self.idToTitle[task['id']] = task['title']
        # Set everything to be initially unmodified
        task['modified'] = Tasky.UNCHANGED
        self.taskLists[tasklist['id']][task['id']] = task

  def PutData(self):
    # Nothing to write home about
    if self.taskLists == {}:
      return

    for tasklistID in self.taskLists:
      for taskID in self.taskLists[tasklistID]:
        task = self.taskLists[tasklistID][taskID]
        if task['modified'] is Tasky.UNCHANGED:
          continue
        elif task['modified'] is Tasky.MODIFIED:
          self.service.tasks().update(
            tasklist=tasklistID, task=taskID, body=task).execute()
        elif task['modified'] is Tasky.DELETED:
          self.service.tasks().delete(
            tasklist=tasklistID, task=taskID).execute()

  def PrintAllTasks(self, tasklistID):
    tab = '  '

    # No task lists
    if self.taskLists == {}:
      print 'Found no task lists.'
      return

    # Use a dictionary to store the indent depth of each task
    depthMap = {tasklistID: 0}
    depth = 1

    # Print task name
    if len(self.taskLists[tasklistID]) == 0:
      print (TextColor.HEADER, self.idToTitle[tasklistID], TextColor.ENDC,
             '(empty)')
    else:
      print TextColor.HEADER, self.idToTitle[tasklistID], TextColor.ENDC

    for taskID in self.taskLists[tasklistID]:
      task = self.taskLists[tasklistID][taskID]
      if task['modified'] is Tasky.DELETED:
        continue
      depth = 1
      isCompleted = (task['status'] == 'completed')

      # Set the depth of the current task
      if 'parent' in task and task['parent'] in depthMap:
        depth = depthMap[task['parent']] + 1
      depthMap[task['id']] = depth

      # Print x in box if task has already been completed
      if isCompleted:
        print ('%s%s [x] %s' % (
               tab * depth, self.taskLists[tasklistID].keys().index(taskID),
               task['title']))
      else:
        print ('%s%s%s [ ] %s%s' % (
               TextColor.TITLE, tab * depth,
               self.taskLists[tasklistID].keys().index(taskID), task['title'],
               TextColor.ENDC))

      # Print due date if specified
      if 'due' in task:
        date = dt.datetime.strptime(task['due'],
                                    '%Y-%m-%dT%H:%M:%S.%fZ')
        output = date.strftime('%a, %b %d, %Y')
        print ('%s%sDue Date: %s%s' % (
               tab * (depth + 1), TextColor.DATE,
               output, TextColor.ENDC))

      # Print notes if specified
      if 'notes' in task:
        print ('%s%sNotes: %s%s' % (
               tab * (depth + 1), TextColor.NOTES, task['notes'],
               TextColor.ENDC))

  def PrintSummary(self):
    for tasklistID in self.taskLists:
      print ('%s %s (%s)' % (
             self.taskLists.keys().index(tasklistID),
             self.idToTitle[tasklistID], len(self.taskLists[tasklistID])))

  def HandleInputArgs(self, args, atasklistID=0):
    action = ''.join(args['action'])
    args['list'] = int(args['list'])
    if atasklistID == 0:
      atasklistID = args['list']
    tasklistID = self.taskLists.keys()[atasklistID]
    tasklist = self.taskLists[tasklistID]

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
        print 'Adding task...'
        self.AddTask(atasklistID, task)
    if action is 'd':
      readIn = raw_input('This will delete the list "' +
                         self.idToTitle[tasklistID] +
                         ('" and all its contents permanently. Are you sure?',
                          '(y/n): '))
      if readIn is 'Y' or readIn is 'y':
          self.service.tasklists().delete(tasklist=tasklistID).execute()
      del self.taskLists[tasklistID]
      self.PrintSummary()
      self.PutData()
      sys.exit(True)
    if action is 'n':
      if args['rename'] is True:
        print 'Renaming task list...'
        tasklist = self.service.tasklists().get(tasklist=tasklistID).execute()
        tasklist['title'] = args['title'][0]
        self.idToTitle[tasklistID] = args['title'][0]
        self.service.tasklists().update(
            tasklist=tasklistID,
            body=tasklist
            ).execute()
        time.sleep(3)
      else:
        print 'Creating new task list...'
        newTaskList = self.service.tasklists().insert(
            body={'title': args['title']}).execute()
        self.idToTitle[newTaskList['id']] = newTaskList['title']
        self.taskLists[newTaskList['id']] = OrderedDict()
      self.PrintSummary()
      self.PutData()
      sys.exit(True)
    #elif tasklist == {}:
        #print(IDToTitle[tasklistID], '(empty)')
        #return
    elif action is 'e':
      print 'Editing task...'
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
      if task['modified'] == Tasky.DELETED:
        return
      task['modified'] = Tasky.MODIFIED
    elif action is 'm':
      print 'Moving task...'
      task = tasklist[tasklist.keys()[int(args['index'][0])]]
      self.MoveTask(atasklistID, task, args)
      self.PutData()
      sys.exit(True)
    elif action is 'c':
      if args['all'] is True:
        print 'Removing all tasks...'
        for taskID in tasklist:
          self.RemoveTask(atasklistID, tasklist[taskID])
      else:
        print 'Clearing completed tasks...'
        self.service.tasks().clear(tasklist=tasklistID).execute()
        for taskID in tasklist:
          task = tasklist[taskID]
          if task['status'] == 'completed':
            task['modified'] = Tasky.DELETED
    elif action is 'r':
      print 'Removing task...'
      for index in args['index']:
        index = int(index)
        self.RemoveTask(atasklistID, tasklist[tasklist.keys()[index]])
    elif action is 't':
      print 'Toggling task...'
      for index in args['index']:
        index = int(index)
        self.ToggleTask(atasklistID, tasklist[tasklist.keys()[index]])

    if action is 'l' and args['all'] is True:
      for tasklistID in self.taskLists:
        self.PrintAllTasks(tasklistID)
    elif action is 'l' and args['summary'] is True:
      self.PrintSummary()
    elif action is 'i':
      self.ReadLoop(args, atasklistID)
    else:
      self.PrintAllTasks(tasklistID)

  def Authenticate(self):
    f = Auth(KEYS_FILE)

    # OAuth 2.0 Authentication
    flow = OAuth2WebServerFlow(
      client_id=f.GetClientId(),
      client_secret=f.GetClientSecret(),
      scope='https://www.googleapis.com/auth/tasks',
      user_agent='Tasky/v1')

    # If credentials don't exist or are invalid, run through the native client
    # flow. The Storage object will ensure that if successful, the good
    # Credentials will get written back to a file.
    storage = Storage(os.path.join(TASKY_DIR, 'tasks.dat'))
    credentials = storage.get()

    if credentials is None or credentials.invalid:
      credentials = run(flow, storage)

    http = httplib2.Http()
    http = credentials.authorize(http)

    # The main Tasks API object
    self.service = build(
      serviceName='tasks', version='v1', http=http,
      developerKey=f.GetApiKey())

  def ReadLoop(self, args, tasklistID=0):
    while True:
      readIn = raw_input(USAGE)
      if readIn is '' or readIn is 'q':
        break
      args = shlex.split(readIn)
      args[:0] = '/'
      args = ParseArguments(args)
      self.HandleInputArgs(args, tasklistID)


def main(args):
  tasky = Tasky()
  parsedArgs = ParseArguments(args)

  if len(args) > 1:
    tasky.HandleInputArgs(parsedArgs)
  else:
    tasky.ReadLoop(parsedArgs)

  # Push final changes before exiting
  tasky.PutData()


if __name__ == '__main__':
  main(sys.argv)
