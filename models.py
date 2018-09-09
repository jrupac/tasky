#!/usr/bin/env python3.7

from __future__ import annotations
from collections.__init__ import OrderedDict
from operator import attrgetter
from typing import Dict, Optional, List, Any
import datetime as dt


class Task(object):
  """Class to manage a single task."""

  DEFAULT = 0
  MODIFIED = 1
  DELETED = 2

  def __init__(self, item):
    self._id = item.get('id')
    self._title = item.get('title')
    self._parent = item.get('parent')
    self._position = item.get('position')
    self._notes = item.get('notes')
    self._status = Task.DEFAULT
    if item.get('due') is not None:
      self._due = dt.datetime.strptime(
        item.get('due'), '%Y-%m-%dT%H:%M:%S.%fZ')
    else:
      self._due = None
    self._completed = item['status'] == 'completed'
    self._childTasks: Dict[str, Task] = {}

  @property
  def Id(self) -> str:
    return self._id

  @property
  def Position(self) -> str:
    return self._position

  @property
  def Parent(self) -> Optional[str]:
    return self._parent

  def SetParent(self, pId: Optional[str]) -> None:
    if self._status == Task.DELETED:
      return
    self._parent = pId

  def Delete(self, force: bool = False) -> None:
    if not force and self._completed:
        self._SetStatus(Task.DELETED)
    self._SetStatus(Task.DELETED)

  def IsDeleted(self) -> bool:
    return self._status == Task.DELETED

  def IsModified(self) -> bool:
    return self._status in (Task.DELETED, Task.MODIFIED)

  def Modify(self, items: Dict[str, Any]) -> None:
    if 'title' in items:
      self._title = items['title']
    if 'due' in items:
      self._due = items['due']
    if 'notes' in items:
      self._notes = items['notes']
    self._status = Task.MODIFIED

  def Toggle(self) -> None:
    for task in self._childTasks.values():
      task._completed = not self._completed
    self._completed = not self._completed
    self._SetStatus(Task.MODIFIED)

  def _SetStatus(self, status: int) -> None:
    if self._status == Task.DELETED:
      return
    self._status = status
    for task in self._childTasks.values():
      task._SetStatus(status)

  def AddChildTask(self, task: Task) -> None:
    if self._status == Task.DELETED:
      return
    self._childTasks[task.Id] = task

  def RemoveChildTask(self, task: Task) -> None:
    if self._status == Task.DELETED:
      return
    self._childTasks.pop(task.Id)

  def GetChildTask(self, cId: str) -> Optional[Task]:
    return self._childTasks.get(cId)

  def GetChildTasks(self) -> List[Task]:
    return list(sorted(self._childTasks.values(), key=attrgetter('Position')))

  def GetResource(self) -> Dict[str, Any]:
    r = {'kind': 'tasks#task',
         'id': self._id,
         'title': self._title,
         'parent': self._parent,
         'position': self._position,
         'status': 'completed' if self._completed else 'needsAction',
         'deleted': self._status == Task.DELETED}
    if self._notes is not None:
      r['notes'] = self._notes
    if self._due is not None:
      r['due'] = self._due
    return r

  def PrintTask(self, idx: int, tab: str, summary: bool = False) -> None:
    if self._completed:
      print('%s%s [x] %s' % (tab, idx, self._title))
    else:
      print('%s%s%s [ ] %s%s' % (
        TextColor.TITLE, tab, idx, self._title, TextColor.CLEAR))

    if not summary:
      if self._due:
        date = self._due.strftime('%a, %b %d, %Y')
        print('%s%sDue Date: %s%s' % (
          2 * tab, TextColor.DATE, date, TextColor.CLEAR))
      if self._notes:
        print('%s%sNotes: %s%s' % (
          2 * tab, TextColor.NOTES, self._notes, TextColor.CLEAR))


class TaskList(object):
  """Class to manage a single list of tasks."""

  def __init__(self, item):
    self._id: str = item.get('id')
    self._title: str = item.get('title')
    self._tasks: Dict[str, Task] = OrderedDict()

  @property
  def Id(self) -> str:
    return self._id

  @property
  def Title(self) -> str:
    return self._title

  def SetTitle(self, title: str) -> None:
    self._title = title

  def AddTask(self, task: Task) -> None:
    self._tasks[task.Id] = task

  def RemoveTask(self, task: Task) -> None:
    if task.Parent:
      self._tasks.get(task.Parent).RemoveChildTask(task)
    if task in self._tasks:
      self._tasks.pop(task.Id)

  def UpdateNesting(self) -> None:
    for v in list(self._tasks.values()):
      pId = v.Parent
      if pId is not None:
        p = self._tasks.get(pId)
        if p is None:
          print('Warning: parent task not found: %s' % pId)
          v.SetParent(None)
        else:
          p.AddChildTask(v)
          self._tasks.pop(v.Id)

  def GetNumTasks(self) -> int:
    return len(self.GetTasks())

  def GetTasks(self, include_deleted: bool = False) -> List[Task]:
    tasks: List[Task] = []
    for t in sorted(self._tasks.values(), key=attrgetter('Position')):
      if include_deleted or not t.IsDeleted():
        tasks.append(t)
        tasks.extend(t.GetChildTasks())
    return tasks

  def GetTaskByPos(self, pos: int) -> Task:
    return self.GetTasks()[pos]

  def GetTask(self, cId: str, pId: str = None) -> Optional[Task]:
    if pId is not None:
      if pId not in self._tasks:
        print('Error: Invalid parent ID: %s' % pId)
      return self._tasks[pId].GetChildTask(cId)
    return self._tasks.get(cId)

  def GetResource(self) -> Dict[str, Any]:
    r = {'kind': 'tasks#taskList',
         'id': self._id,
         'title': self._title}
    return r

  def PrintTaskList(self, idx: int, summary: bool = False) -> None:
    self.UpdateNesting()

    if self.GetNumTasks() == 0:
      print(
        ('%d %s%s%s (empty)' % (
          idx, TextColor.HEADER, self._title, TextColor.CLEAR)))
    else:
      print(
        ('%d %s%s%s' % (idx, TextColor.HEADER, self._title, TextColor.CLEAR)))

    tab = '  '
    for taskIdx, task in enumerate(self.GetTasks()):
      if task.Parent is not None:
        task.PrintTask(taskIdx, 2 * tab, summary)
      else:
        task.PrintTask(taskIdx, tab, summary)


class TaskLists(object):
  """Class to manage multiple task lists."""

  def __init__(self):
    self._taskLists: List[TaskList] = []

  def AddTaskList(self, tasklist: TaskList) -> None:
    self._taskLists.append(tasklist)

  def DeleteTaskList(self, tasklist: TaskList) -> None:
    self._taskLists.remove(tasklist)

  def GetTaskLists(self) -> List[TaskList]:
    return self._taskLists

  def GetTaskListByPos(self, pos: int) -> Optional[TaskList]:
    if pos > len(self._taskLists) - 1:
      return None
    return self._taskLists[pos]

  def PrintTaskLists(self, summary: bool) -> None:
    for idx, taskList in enumerate(self._taskLists):
      if summary:
        print('%s %s (%s)' % idx, taskList.Title, taskList.GetNumTasks())
      else:
        taskList.PrintTaskList(idx, summary)


class TextColor(object):
  """A class to provide terminal keycodes for colored output."""

  HEADER = '\033[1;38;5;218m'
  DATE = '\033[1;38;5;249m'
  NOTES = '\033[1;38;5;252m'
  TITLE = '\033[1;38;5;195m'
  CLEAR = '\033[0m'