from unittest import TestCase, mock

import tasky


class TaskyTest(TestCase):

  def setUp(self):
    self._tasky = tasky.Tasky()

  @mock.patch.object(tasky, 'build')
  @mock.patch.object(tasky, 'httplib2')
  @mock.patch.object(tasky, 'Auth', autospec=True)
  def _TestAuthenticateHelper(
      self, credentials, web_server_flow, storage, auth, httplib2, build):
    storage.return_value.get.return_value = credentials
    http_mock = mock.MagicMock()
    httplib2.Http.return_value = http_mock
    credentials.authorize.return_value = http_mock

    self._tasky.Authenticate()

    auth.assert_called_once_with(tasky.KEYS_FILE)
    web_server_flow.assert_called_once_with(
        client_id=auth.return_value.GetClientId.return_value,
        client_secret=auth.return_value.GetClientSecret.return_value,
        scope='https://www.googleapis.com/auth/tasks',
        user_agent='Tasky/v1')

    httplib2.Http.assert_called_once_with()
    credentials.authorize.assert_called_once_with(http_mock)
    build.assert_called_once_with(
        serviceName='tasks', version='v1', http=http_mock,
        developerKey=auth.return_value.GetApiKey.return_value)

  @mock.patch.object(tasky, 'Storage')
  @mock.patch.object(tasky, 'OAuth2WebServerFlow')
  def test_Authenticate_InvalidCredentials(self, web_server_flow, storage):
    credentials = mock.MagicMock()

    with mock.patch.object(tasky, 'run') as run:
      run.return_value = credentials
      self._TestAuthenticateHelper(credentials, web_server_flow, storage)
      run.assert_called_once_with(
          web_server_flow.return_value, storage.return_value)

  @mock.patch.object(tasky, 'Storage')
  @mock.patch.object(tasky, 'OAuth2WebServerFlow')
  def test_Authenticate_ValidCredentials(self, web_server_flow, storage):
    credentials = mock.MagicMock()
    credentials.invalid = False

    with mock.patch.object(tasky, 'run') as run:
      self._TestAuthenticateHelper(credentials, web_server_flow, storage)
      run.assert_not_called()

  def test_GetData_AlreadyCalled(self):
    with mock.patch.object(self._tasky, 'service') as service:
      tasklists_list = service.tasklists.return_value.list
      tasklists_list.return_value.execute.return_value = {'items': []}

      self._tasky.GetData()
      self._tasky.GetData()

      tasklists_list.return_value.execute.assert_called_once_with()

  def test_GetData_OneTaskListWithItem(self):
    with mock.patch.object(self._tasky, 'service') as service:
      tasklists_list = service.tasklists.return_value.list
      tasklists_list.return_value.execute.return_value = {
        'items': [{'id': '1', 'title': 'tasklist1'}]}

      tasks_list = service.tasks.return_value.list
      tasks_list.return_value.execute.return_value = {
        'items': [{'id': '1', 'title': 'task1', 'status': 'completed'}]
      }

      self._tasky.GetData()

      self.assertEqual(1, len(self._tasky._taskLists.GetTaskLists()))
      taskList = self._tasky._taskLists.GetTaskListByPos(0)
      self.assertEqual(1, taskList.GetNumTasks())
      task = taskList.GetTaskByPos(0)
      self.assertEqual('1', task.Id)

  def test_GetData_TwoTaskLists(self):
    with mock.patch.object(self._tasky, 'service') as service:
      tasklists_list = service.tasklists.return_value.list
      tasklists_list.return_value.execute.return_value = {
        'items': [
          {'id': '1', 'title': 'tasklist1'},
          {'id': '2', 'title': 'tasklist2'}
        ]}

      self._tasky.GetData()
      self.assertEqual(2, len(self._tasky._taskLists.GetTaskLists()))

  def test_AddTask(self):
    pass

  def test_MoveTask(self):
    pass

  def test_RemoveTask(self):
    pass

  def test_ToggleTask(self):
    pass

  def test_GetData(self):
    pass

  def test_PutData(self):
    pass

  def test_PrintAllTaskLists(self):
    pass

  def test_PrintAllTasks(self):
    pass

  def test_PrintSummary(self):
    pass

  def test_HandleInputArgs(self):
    pass
