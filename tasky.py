#!/usr/bin/env python3.7

"""
A Google Tasks command line interface.
"""
from __future__ import annotations

import datetime
import os
# The "readline" module is imported for side effects.
# noinspection PyUnresolvedReferences
import readline
import shlex
import sys
import time
from typing import Optional, Dict, Any

import httplib2
from absl import flags as gflags
# The modules in apiclient are dynamically added.
# noinspection PyUnresolvedReferences
from apiclient.discovery import build
# noinspection PyUnresolvedReferences
from apiclient.discovery import Resource
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.file import Storage
from oauth2client.tools import run_flow as run

from models import Task, TaskList, TaskLists, TextColor

__author__ = 'Ajay Roopakalu (https://github.com/jrupac/tasky)'

FLAGS = gflags.FLAGS

# Flags related to operations on task lists.
gflags.DEFINE_boolean(
  'add', False, 'Add operation', short_name='a')
gflags.DEFINE_boolean(
  'clear', False, 'Clear operation', short_name='c')
gflags.DEFINE_boolean(
  'delete', False, 'Delete operation', short_name='d')
gflags.DEFINE_boolean(
  'edit', False, 'Edit operation', short_name='e')
gflags.DEFINE_boolean(
  'list', False, 'List operation', short_name='l')
gflags.DEFINE_boolean(
  'move', False, 'Move operation', short_name='m')
gflags.DEFINE_boolean(
  'new', False, 'New operation', short_name='n')
gflags.DEFINE_boolean(
  'remove', False, 'Remove operation', short_name='r')
gflags.DEFINE_boolean(
  'rename', False, 'Rename operation.', short_name='rn')
gflags.DEFINE_boolean(
  'summary', False, 'Print a summary of the task lists.', short_name='s')
gflags.DEFINE_boolean(
  'toggle', False, 'Toggle operation', short_name='t')
gflags.DEFINE_boolean(
  'quit', False, 'Quit operation', short_name='q')

# Flags related to options on above operations.
gflags.DEFINE_integer(
  'after', -1, 'The index of the task that this should be after')
gflags.DEFINE_string(
  'date', '', 'A date in MM/DD/YYYY format.')
gflags.DEFINE_spaceseplist(
  'index', '', 'Index of task.', short_name='i')
gflags.DEFINE_boolean(
  'force', False, 'Forcibly perform the operation.', short_name='f')
gflags.DEFINE_boolean(
  'color', True, 'Display output with terminal colors.', short_name='o')
gflags.DEFINE_string(
  'note', '', 'A note to attach to a task.')
gflags.DEFINE_integer(
  'parent', 0, 'Index of parent task.', short_name='p')
gflags.DEFINE_integer(
  'tasklist', 0, 'Id of task list to operate on.')
gflags.DEFINE_string(
  'title', '', 'The name of the task.')


USAGE = ('[-a]dd, [-c]lear, [-d]elete, [-e]dit, [-r]emove task, ' +
         '[-m]ove, [-n]ew list, -rename/-rn, [-s]ummary, [-t]oggle, ' +
         '[-q]uit: ')

# Environment constants
TASKY_DIR = os.path.join(os.environ['HOME'], '.tasky')
KEYS_FILE = os.path.join(TASKY_DIR, 'keys.txt')


class Auth(object):
  """A class to handle persistence and access of various OAuth keys."""

  def __init__(self, keyFile):
    try:
      with open(keyFile, 'r') as self.f:
        self.clientId: str = self.f.readline().rstrip()
        self.clientSecret: str = self.f.readline().rstrip()
        self.apiKey: str = self.f.readline().rstrip()
    except IOError:
      self.clientId: str = input("Enter your clientID: ")
      self.clientSecret: str = input("Enter your client secret: ")
      self.apiKey: str = input("Enter your API key: ")
      self._WriteAuth()

  def _WriteAuth(self) -> None:
    if not os.path.exists(TASKY_DIR):
      os.makedirs(TASKY_DIR)
    with open(KEYS_FILE, 'w') as self.auth:
      self.auth.write(str(self.clientId) + '\n')
      self.auth.write(str(self.clientSecret) + '\n')
      self.auth.write(str(self.apiKey) + '\n')

  def GetClientId(self) -> str:
    return self.clientId

  def GetClientSecret(self) -> str:
    return self.clientSecret

  def GetApiKey(self) -> str:
    return self.apiKey


class Tasky(object):
  """Main class that handles task manipulation."""

  def __init__(self):
    self._taskLists: TaskLists = None
    self.service: Resource = None

  def Authenticate(self) -> None:
    """Runs authentication flow and returns service object."""
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

    # The main Tasks API object.
    self.service = build(
      serviceName='tasks', version='v1', http=http,
      developerKey=f.GetApiKey())

  def GetData(self) -> None:
    # Only retrieve data once per run
    if self._taskLists is not None:
      return

    self._taskLists = TaskLists()
    resp = self.service.tasklists().list().execute()

    for tl in resp['items']:
      taskList = TaskList(tl)

      tasks = self.service.tasks().list(tasklist=tl['id']).execute()
      if 'items' in tasks:
        for t in tasks['items']:
          taskList.AddTask(Task(t))

      taskList.UpdateNesting()
      self._taskLists.AddTaskList(taskList)

  def AddTask(self, taskList: TaskList, res: Dict[str, Any]) -> None:
    if 'parent' in res:
      parentTask = taskList.GetTaskByPos(res['parent'])
      # Forbid sub-sub-tasks.
      if parentTask.Parent is not None:
        print('Warning: sub-sub-tasks not allowed; moving to top-level.')
        resource = self.service.tasks().insert(
          tasklist=taskList.Id, body=res).execute()
      else:
        resource = self.service.tasks().insert(
          tasklist=taskList.Id, parent=parentTask.Id,
          body=res).execute()
    else:
      resource = self.service.tasks().insert(
        tasklist=taskList.Id, body=res).execute()

    taskList.AddTask(Task(resource))

  def MoveTask(
      self, taskList: TaskList, task: Task, after: Optional[Task],
      parent: Optional[Task]) -> None:
    taskList.RemoveTask(task)

    if parent is not None:
      res = self.service.tasks().move(
        tasklist=taskList.Id, task=task.Id, parent=parent.Id).execute()
    elif after is not None:
      res = self.service.tasks().move(
        tasklist=taskList.Id, task=task.Id, previous=after.Id).execute()
    else:
      # Shouldn't happen
      return

    taskList.AddTask(Task(res))

  def DeleteTaskList(self, taskList: TaskList) -> None:
    self._taskLists.DeleteTaskList(taskList)
    self.service.tasklists().delete(tasklist=taskList.Id).execute()

  def AddTaskList(self, title: str) -> None:
    res = self.service.tasklists().insert(body={'title': title}).execute()
    taskList = TaskList(res)
    self._taskLists.AddTaskList(taskList)

  def RenameTaskList(self, taskList: TaskList, title: str) -> None:
    taskList.SetTitle(title)
    self.service.tasklists().update(
      tasklist=taskList.Id, body=taskList.GetResource()).execute()

  def PutData(self):
    # Nothing to write home about
    if self._taskLists is None:
      return

    for taskList in self._taskLists.GetTaskLists():
      for task in taskList.GetTasks(include_deleted=True):
        if task.IsModified():
          self.service.tasks().update(
            tasklist=taskList.Id, task=task.Id,
            body=task.GetResource()).execute()

  def PrintTaskList(self, pos: int, summary: bool = False) -> None:
    self._taskLists.GetTaskListByPos(pos).PrintTaskList(pos, summary)

  def PrintAllTaskLists(self, summary: bool = False) -> None:
    self._taskLists.PrintTaskLists(summary)

  def HandleInputArgs(self):
    taskList = None
    if FLAGS['tasklist'].present:
      taskList = self._taskLists.GetTaskListByPos(FLAGS.tasklist)
      taskList.UpdateNesting()

    # First off, check if we should be displaying in color or not.
    if not FLAGS.color:
      TextColor.HEADER = ''
      TextColor.DATE   = ''
      TextColor.NOTES  = ''
      TextColor.TITLE  = ''
      TextColor.CLEAR  = ''

    if FLAGS.add:
      res = {'title': FLAGS.title}
      if FLAGS['date'].present:
        d = datetime.datetime.strptime(FLAGS.date, "%m/%d/%Y")
        res['due'] = d.strftime('%Y-%m-%dT12:00:00.000Z')
      if FLAGS['note'].present:
        res['notes'] = FLAGS.note
      if FLAGS['parent'].present:
        res['parent'] = FLAGS.parent

      print('Adding task...')
      self.AddTask(taskList, res)
    elif FLAGS.move:
      pos = int(FLAGS.index[0])
      task = taskList.GetTaskByPos(pos)

      after, parent = None, None
      if FLAGS['after'].present and FLAGS['parent'].present:
        print('Only one of "after" and "parent" flags are allowed.')
        return
      elif FLAGS['after'].present:
        after = taskList.GetTaskByPos(FLAGS.after)
      elif FLAGS['parent'].present:
        parent = taskList.GetTaskByPos(FLAGS.parent)
      else:
        print('One of "after" or "parent" must be specified.')
        return

      print('Moving task...')
      self.MoveTask(taskList, task, after, parent)
    elif FLAGS.delete:
      readIn = input(
        'This will delete the list "' + taskList.Title +
        '" and all its contents permanently. Are you sure? (y/n): ')
      if readIn in ['y', 'Y']:
        print('Removing tasklist...')
        self.DeleteTaskList(taskList)
    elif FLAGS.remove:
      print('Removing task(s)...')
      for index in FLAGS.index:
        pos = int(index)
        taskList.GetTaskByPos(pos).Delete(force=True)
    elif FLAGS.toggle:
      print('Toggling task(s)...')
      for index in FLAGS.index:
        pos = int(index)
        taskList.GetTaskByPos(pos).Toggle()
    elif FLAGS.new:
      if not FLAGS.title:
        print('WARNING: Creating task list with no title.')
      print('Creating new task list...')
      self.AddTaskList(FLAGS.title)
    elif FLAGS.rename:
      if not FLAGS.title:
        print('WARNING: New task list name is empty.')
      print('Renaming task list...')
      self.RenameTaskList(taskList, FLAGS.title)
    elif FLAGS.edit:
      pos = int(FLAGS.index[0])
      task = taskList.GetTaskByPos(pos)

      res = {}
      if FLAGS.title:
        res['title'] = FLAGS.title
      if FLAGS.date:
        d = time.strptime(FLAGS.date, "%m/%d/%Y")
        res['due'] = (str(d.tm_year) + '-' +
                       str(d.tm_mon) + '-' +
                       str(d.tm_mday) +
                       'T12:00:00.000Z')
      if FLAGS.note:
        res['notes'] = FLAGS.note

      print('Editing task...')
      task.Modify(res)
    elif FLAGS.clear:
      if FLAGS.force:
        print('Removing all task(s)...')
      else:
        print('Clearing completed task(s)...')
      for task in taskList.GetTasks():
        task.Delete(force=FLAGS.force)
    elif FLAGS.list:
      if taskList:
        print('Printing Task List %d...' % FLAGS.tasklist)
        taskList.PrintTaskList(FLAGS.tasklist, summary=FLAGS.summary)
      else:
        print('Printing all task lists...')
        self.PrintAllTaskLists(summary=FLAGS.summary)


def ReadLoop(tasky):
  while True:
    # In the interactive case, display the list before any operations unless
    # the previous operation was a --list.
    if not FLAGS['list'].present:
      if FLAGS.summary:
        tasky.PrintSummary()
      else:
        tasky.PrintAllTaskLists()

    readIn = input(USAGE)
    # Prepend a string to hold the place of the application name.
    args = [''] + shlex.split(readIn)

    # Re-populate flags based on this input.
    FLAGS.unparse_flags()
    FLAGS(args)

    if FLAGS.quit:
      break
    tasky.HandleInputArgs()


def main(args):
  FLAGS(args)

  tasky = Tasky()
  tasky.Authenticate()
  tasky.GetData()

  if len(args) > 1:
    tasky.HandleInputArgs()

    # In the non-interactive case, print task list after the operation unless
    # --list was the operation just performed.
    if not FLAGS['list'].present:
      if FLAGS['tasklist'].present:
        tasky.PrintTaskList(FLAGS.tasklist, summary=FLAGS.summary)
      else:
        tasky.PrintAllTaskLists(summary=FLAGS.summary)
  else:
    ReadLoop(tasky)

  # Push any final changes before exiting.
  tasky.PutData()


if __name__ == '__main__':
  main(sys.argv)
