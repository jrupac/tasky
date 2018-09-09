# Tasky

## Description
[Tasky][tasky] is a command-line interface to Google's Tasks API. It is meant to
parallel the functionality of [Todo.txt][todotxt].

## Dependencies
Requires Python 3.7, [Google API client for Python](https://code.google.com/p/google-api-python-client/),
[absl-py](https://github.com/abseil/abseil-py), [httplib2](https://github.com/httplib2/httplib2) and [oauth2client](https://github.com/google/oauth2client). The needed packages are
installable from PyPi and are in the `requirements.txt` file. Use
`pip install -r requirements.txt` to install them. Ensure your pip command points to your pip3 path.

**NOTE**: The script will create a `~/.tasky/keys.txt` file that persists your
API credentials on disk. Take care not to commit this data into any public
repositories. You are responsible for securing your keys!

## Installation

### Connecting to the Tasks API
1. Go to https://cloud.google.com/console/project
2. Create a project.
3. Enable the Tasks API (disable everything else).
4. Go to the credentials screen.
5. Click the "Create new Key" button under the Public API access section.
6. Generate a browser key and leave the URL restriction blank.
7. Click the "Generate new Client ID" under Oauth.
8. Select "Installed application -> Other"
9. Make sure you've chosen product name and email adress under the "Consent screen".
10. Run ./tasky.py and enter the clientID, client secret and API key.

### Local

Many [Todo.txt][todotxt] users rename the script to simply 't'. I recommend something similar; however, for clarity's sake I will refer to the script as 'tasky' for this documentation.

      ln -s /dir/for/tasky.py /folder/in/$PATH/tasky

# Usage Examples

## Task List Operations

### List (--list, -l):
   * List all tasks across all task lists.
   * The (--summary, -s) flag will only print a summary of each task lists.

```bash
    $ tasky -l
    0 To-Do
       0 [ ] Buy birthday card
         Note: Also get flowers.
       1 [ ] Groceries
         2 [ ] Eggs
         3 [ ] Bread
         4 [ ] Milk
    1 Movies
       0 [ ] The Matrix

    $ tasky -l -s
    0 To-Do ( 5 )
    1 Movies ( 1 )
```
### New List (--new, -n):
   * Creates a new task list with the title specified by (--title, -t).
   * The (--summary, -s) flag will only print a summary of each task lists.

```bash
    $ tasky -n --title "My New List" -s
    Creating new task list...
    0 To-Do ( 5 )
    1 Movies ( 1 )
    2 My New List ( 0 )
```
### Rename List (--rename, -r):
   * Rename an existing task list specified by (--tasklist) with the title
     specified by (--title, -t).
   * The (--summary, -s) flag will only print a summary of each task lists.

```bash
    $ tasky -r --title "Books" --tasklist 2 -s
    Renaming task list...
    0 To-Do ( 5 )
    1 Movies ( 1 )
    2 Books ( 0 )
```
### Delete List (--delete, -d):
   * Deletes the task list specified by (--tasklist).
   * The (--summary, -s) flag will only print a summary of each task lists.

```bash
    $ tasky -d --tasklist 2 -s
    This will delete the list "Books" and all its contents permanently. Are you sure? (y/n): y
    0 To-Do ( 5 )
    1 Movies ( 1 )
```
## Task Operations

### Adding a task (--add, -a):
   * Add a task to the task list specified by (--tasklist), with title specified
     by (--title), due date specified in MM/DD/YYYY format by (--date), note
     specified by (--note), and parent specified by (--parent).
   * The (--summary, -s) flag will only print a summary of each task lists.

```bash
    $ tasky -a --title 'Do laundry' --note "And fold!" --date "1/1/2014"
    0 To-Do
       0 [ ] Do laundry
         Note: And fold!
         Due: January 1, 2014
       1 [ ] Buy birthday card
         Note: Also get flowers.
       2 [ ] Groceries
         3 [ ] Eggs
         4 [ ] Bread
         5 [ ] Milk
    1 Movies
       0 [ ] The Matrix
```
### Editing a task (--edit, -e):
   * Edit a task in the task list specified by (--tasklist) with index
     (--index, -i) and set title specified by (--title), due date specified in
     MM/DD/YYYY format by (--date), note specified by (--note), and parent
     specified by (--parent).
   * The (--summary, -s) flag will only print a summary of each task lists.

```bash
    $ tasky -e -i 0 --date "2/1/2014"
    0 To-Do
       0 [ ] Do laundry
         Note: And fold!
         Due: February 1, 2014
       1 [ ] Buy birthday card
         Note: Also get flowers.
       2 [ ] Groceries
         3 [ ] Eggs
         4 [ ] Bread
         5 [ ] Milk
    1 Movies
       0 [ ] The Matrix
```
### Toggling a task and its children (--toggle, -t):
   * Toggle the completed state of a task in the task list specified by
     (--tasklist) with index (--index, -i) and its children tasks.
   * The (--index, -i) can also take a space-separated string to remove multiple
     tasks.
   * The (--summary, -s) flag will only print a summary of each task lists.

```bash
    $ tasky -t -i 2
    0 To-Do
       0 [ ] Do laundry
         Note: And fold!
         Due: February 1, 2014
       1 [ ] Buy birthday card
         Note: Also get flowers.
       2 [x] Groceries
         3 [x] Eggs
         4 [x] Bread
         5 [x] Milk
    1 Movies
       0 [ ] The Matrix
```
### Removing a task and its children (--remove, -r):
   * Remove a task in the task list specified by (--tasklist) with index
     (--index, -i) and its children tasks.
   * The (--index, -i) can also take a space-separated string to remove multiple
     tasks.
   * The (--summary, -s) flag will only print a summary of each task lists.

```bash
    $ tasky -r -i 2
    0 To-Do
       0 [ ] Do laundry
         Note: And fold!
         Due: February 1, 2014
       1 [ ] Buy birthday card
         Note: Also get flowers.
    1 Movies
       0 [ ] The Matrix
```
### Clearing tasks (--clear, -c):
   * Clear all completed tasks in the task list specified by (--tasklist).
   * If the (--force, -f) flag is set, also clear non-completed tasks.
   * The (--summary, -s) flag will only print a summary of each task lists.

```bash
    # Set one task as completed first
    $ tasky -t -i 0 -s
    0 To-Do ( 2 )
    1 Movies ( 1 )

    $ tasky -c -i 2
    0 To-Do
       0 [ ] Do laundry
         Note: And fold!
         Due: February 1, 2014
    1 Movies
       0 [ ] The Matrix
```
### Moving tasks (--move, -m):
   * Move a task in the task list specified by (--tasklist) with index specified
     by (--index, -i) to a different parent specified by (--parent, -p) or after
     task specified by (--after).

```bash
    # Add another task first
    $ tasky -a --title "Homework"
    0 To-Do
       0 [ ] Homework
       1 [ ] Do laundry
         Note: And fold!
         Due: February 1, 2014
    1 Movies
       0 [ ] The Matrix

    $ tasky -m -i 0 --after 1
    0 To-Do
       0 [ ] Do laundry
         Note: And fold!
         Due: February 1, 2014
       1 [ ] Homework
    1 Movies
       0 [ ] The Matrix
```
## Interactive Mode

  * If you want to make multiple operations in one session, run `tasky` without
    arguments to put it into interactive mode. All the above operations work
    exactly the same way but it is more efficient to run multiple operations
    within one interactive session than separately.

```bash
    $ tasky
    [-a]dd, [-c]lear, [-d]elete, [-e]dit, [-r]emove task, [-l]ist, [-m]ove, [-n]ew list/re[-n]ame, [-s]ummary, [-t]oggle, [-q]uit: -l -s
    0 To-Do ( 2 )
    1 Movies ( 1 )

    [-a]dd, [-c]lear, [-d]elete, [-e]dit, [-r]emove task, [-l]ist, [-m]ove, [-n]ew list/re[-n]ame, [-s]ummary, [-t]oggle, [-q]uit:
    ...
```


## Development/License
Please feel free to list bugs or feature requests on this github page in the
issues section. This script was originally created by
[Ajay Roopakalu](https://github.com/jrupac/tasky), and is under the
[GNU GPL license](http://www.gnu.org/licenses/gpl.txt).

   [tasky]: https://github.com/jrupac/tasky
   [todotxt]: http://todotxt.com/
