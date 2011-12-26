# Tasky.txt

## Description
This is a fork of [Tasky][tasky] which is meant to streamline its ease of use in order to parallel the functionality of [Todo.txt][todotxt]. For example, it uses task and list index numbers as in [Todo.txt][todotxt] instead of title matching as in [Tasky][tasky]. It removes the readline dependency from [Tasky][tasky]. The output is less verbose and the command syntax is slightly changed to facilitate faster typing.

## Dependencies
Requires Python 2.7 and the [Google API client for Python](http://code.google.com/p/google-api-python-client/).

## Installation
Many [Todo.txt][todotxt] users rename the script to simply 't'. I recommend something similar; however, for clarity's sake I will refer to the script as 'tasky' for this documentation.

      chmod +x tasky.py
      ln -s /dir/for/tasky.py /folder/in/$PATH/tasky

## Usage Examples

### List (l):
   * Lists the tasks of the specified list, which defaults to 0.
   * The -s flag will print a summary of your task lists.
   * The -l flag is **universal** and comes _before_ arguments.
   * The -a flag will print all lists and their tasks.

>
      tasky l
      # connermcd's list
      #    0 [ ] Buy birthday card
      #    1 [x] TPS Reports
      #    2 [ ] Groceries
      #      3 [ ] Eggs
      #      4 [ ] Bread
      #      5 [ ] Milk

>
      tasky l -s
      # 0 connermcd's list ( 7 )
      # 1 Movies ( 70 )
      # 2 Testing ( 0 )
      # 3 Mobile ( 0 )

>
      tasky -l 2 l
      # Testing (empty)


>
      tasky l -a
      # -- long list of all tasks in all lists --

### New List (n):
   * Creates a new task list or (-r) renames an old one.

>
      tasky n "My New List"
      tasky -l 2 n -r "New Name"
      # Renaming task list...
      # 0 connermcd's list ( 7 )
      # 1 Movies ( 70 )
      # 2 New Name ( 0 )
      # 3 Mobile ( 0 )
      # 4 My New List ( 0 )

### Delete List (d):
   * Deletes a task list.

### Adding a task (a):
   * tasky a [--help/-h] [--parent/-p <int>] [--date/-d <MM/DD/YYYY>] [--note/-n "<string>"] title\*
   * NOTE: flags must be before the task's title this means that multiple tasks must share the same flags

>
      tasky a Groceries
      tasky a "TPS Reports" "Buy birthday card"
      tasky a -p 2 Eggs Bread Milk "Pasta sauce"
      tasky a -d "5/14/11" -n "This is a note." "Name of task."

### Toggling/removing a task and its children (r):
   * tasky t index\*
   * tasky r index\*

>
      tasky t 2 6 7
      tasky r 6 7
      # Removing task...
      # connermcd's list
      #    0 [ ] Buy birthday card
      #    1 [ ] TPS Reports
      #    2 [x] Groceries
      #      3 [x] Pasta sauce
      #      4 [x] Milk
      #      5 [x] Bread

### Clearing tasks (c):
   * tasky c
      - clears completed tasks for specified list
   * tasky c -a
      - clears all tasks for specified list, completed or not

### Editing tasks (e):
   * Edits the title, date, or note of a task

>
      tasky e 0 -t "Buy Dad's birthday card" -n "Get him a gift card?"
      # Editing task...
      # connermcd's list
      #    0 [ ] Buy Dad's birthday card
      #      Notes: Get him a gift card?
      #    1 [ ] TPS Reports
      #    2 [x] Groceries
      #      3 [x] Pasta sauce
      #      4 [x] Milk
      #      5 [x] Bread

### Moving tasks (m):
   * Move tasks to a different parent or position.
   * The -a/--after tag moves the task after the given index.
   * The -p/--parent task allows you to give a task a new parent.
   * NOTE: The immediate feedback display is still under development...

>
      tasky m 2 -a 0
      # connermcd's list
      #    0 [ ] Buy Dad's birthday card
      #      Notes: Get him a gift card?
      #    1 [x] Groceries
      #      2 [x] Pasta sauce
      #      3 [x] Milk
      #      4 [x] Bread
      #    5 [ ] TPS Reports

>
      tasky m 3 -p 5
      # connermcd's list
      #    0 [ ] Buy Dad's birthday card
      #      Notes: Get him a gift card?
      #    1 [x] Groceries
      #      2 [x] Pasta sauce
      #      3 [x] Bread
      #    4 [ ] TPS Reports
      #      5 [x] Milk

## Development/License
The script currently does very little error catching and still has a few bugs. I plan to iron these out and clean the code. Please feel free to list bugs or feature requests on this github page in the issues section. This script is a fork of the original script created by [Ajay Roopakalu](https://github.com/jrupac/tasky), and has recently been placed under the [GNU GPL license](http://www.gnu.org/licenses/gpl.txt).

   [tasky]: https://github.com/jrupac/tasky
   [todotxt]: http://todotxt.com/
