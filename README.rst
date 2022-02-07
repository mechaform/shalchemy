Shalchemy
=========

For when you get tired of Python and sh and want something in between.


.. code:: python
  
    from shalchemy import sh, run
    from shalchemy.bin import cat, curl, grep
 
    if cat('/etc/hosts') | grep('localhost'):
        run(curl('example.com') > 'file.txt')
        for line in cat('file.txt'):
            print(line)
        run(shalchemy.bin.rm('file.txt'))

Note that none of these are Python functions. We just call the system binaries using ``subprocess`` and do an unhealthy amount of magic to tie everything together.

Installation
============

::

    $> pip install shalchemy

Tutorial
========

There are only three things you need to care about. ``shalchemy.sh``, ``shalchemy.run``, and ``shalchemy.bin``.

You create expressions by chaining ``shalchemy.sh`` instances together.

.. code:: python

    import shalchemy
    ps_aux = shalchemy.sh('ps', 'aux')
    grep = shalchemy.sh('grep', 'python')
    piped_expression = ps_aux | grep

These expressions on their own don't actively run the underlying system commands. They are evaluated in these three circumstances:

- They are passed to ``shalchemy.run``
- They are converted to a ``bool``, ``str``, or ``int``
- They are iterated over

During the evaluation phase, subprocesses are created, files are opened, and things are piped together with Linux magic. The Python process blocks until everything is finished. Once all the processes are done, things are cleaned up, and the correct data type is provided to the user.

Pipes and Redirects
====

shalchemy expressions support pipes ``|`` and redirects (``<``, ``<<``, ``>``, ``>>``) for stdout.

To redirect stderr, there is the ``stderr`` method.

.. code:: python

    from shalchemy import sh, run
    from sqlalchemy.bin import rm
    run(rm('nonexistent_file').stderr('&1') > 'log.txt'))
    run(rm('nonexistent_file2').stderr('somefile') >> 'log.txt'))

Sadly, Python doesn't support the 2> operation.

Arguments
====
``shalchemy.sh`` is used to create expressions. Calling it creates an internal ``CommandExpression``. These ``CommandExpressions`` hold arguments and can curry them. You can also access their properties to naturally generate curried expressions for subcommands. As a result, these four different python lines will create the same ``CommandExpression``:

.. code:: python

    from shalchemy import sh
    from shalchemy.bin import git
    expr1 = sh('git show .')  # Special
    expr2 = sh('git', 'show', '.')
    expr3 = sh(['git', 'show', '.'])
    expr4 = git('show', '.')
    expr5 = git.show('.')

There is something special about ``expr1`` that should be noted. If `sh` (or any ``CommandExpression``) receives a single string as the only argument, it will assume that you wanted to type a sh-compatible string and it'll automatically tokenize it for you using ``shlex``.

In other words, ``sh('git show .')`` will create the Command ``sh(['git', 'show', '.'])``. If you don't like the automatic tokenization, you can explicitly provide a list with a single string inside``sh(['git show .'])``. Note that this second version will attempt to search your ``$PATH`` for a binary named ``git\ show\ .`` which is almost always not what anybody wants. Just a small warning for this special automatic tokenization thing that might become a gotcha one day.

shalchemy.bin
====

The ``shalchemy.bin`` module is a magic module that wraps whatever you want to import in ``shalchemy.sh`` in a straightforward way. Importing ``grep`` from ``sqlalchemy.bin`` will just give you the result of ``sh('grep')``
