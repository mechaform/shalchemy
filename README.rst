Shalchemy
=========

Conveniently call upon binaries from Python as if you were in sh.


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
===================

shalchemy expressions support pipes ``|`` and redirects (``<``, ``>``, ``>>``) for stdout.

Sadly, Python doesn't support overloading the ``2>`` operation for stderr. But because we are crazy, we used ``>=`` instead!

.. code:: python

    from shalchemy import sh
    from sqlalchemy.bin import rm
    sh.run(((rm('nonexistent_file') > 'log.txt') >= '&1')
    sh.run(((rm('nonexistent_file2') >> 'log.txt') >= 'errors.txt')

There are also issues with Python's operator precedence and chaining. That is, ``1 < x < 3`` expands to ``1 < x and x < 3`` which is not very sh-friendly.

If you're going to do any sort of complex redirect chaining, it might be best to use the ``in_``, ``out_`` and ``err_`` methods.

.. code:: python

    from shalchemy import sh
    from sqlalchemy.bin import rm
    sh.run(rm('nonexistent_file').in_('input.txt').out_('log.txt', append=True).err_('&1'))


Arguments
=========

``shalchemy.sh`` is used to create expressions. Calling it creates an internal ``CommandExpression``. These ``CommandExpressions`` hold arguments and curry them. You can also access their attributes to naturally generate curried expressions for subcommands. As a result, these four different python lines will create the same ``CommandExpression``:

.. code:: python

    from shalchemy import sh
    from shalchemy.bin import git
    expr1 = sh('git', 'show', '.')
    expr2 = sh(['git', 'show', '.'])
    expr3 = git('show', '.')
    expr4 = git.show('.')
    expr5 = sh('git show .')  # Special

There is something special about ``expr5`` that should be noted. If `sh` (or any ``CommandExpression``) receives a single string as the only argument, it will assume that you wanted to type a sh-compatible string and it'll automatically tokenize it for you using ``shlex``.

In other words, ``sh('git show .')`` will create the Command ``sh(['git', 'show', '.'])``. If you don't like the automatic tokenization, you can explicitly provide a list with a single string inside like ``sh(['git show .'])``. Note that this second version will attempt to search your ``$PATH`` for a binary named ``"git\ show\ ."`` which is almost always not what anybody wants. Just a small warning for this special automatic tokenization thing that might become a gotcha one day.

shalchemy.bin
=============

The ``shalchemy.bin`` module is a magic module that wraps whatever you want to import in ``shalchemy.sh`` in a straightforward way. Importing ``grep`` from ``sqlalchemy.bin`` will just give you the result of ``sh('grep')``

Multiple commands
=================

shalchemy does not currently (and probably never will) support multiple commands chained with ``&&`` like sh does.


Python IO Redirects
===================

shalchemy supports redirects directly from standard Python io objects. That means this is fully supported:

.. code:: python

    from io import StringIO
    from shalchemy import sh
    from shalchemy.bin import cat
    sh.run(cat < StringIO('my string'))

Process Substitutions
=====================

Process substitution is a technique to make the output of a command
look like a file to the receiving process. One very common use of
this is when using the diff command. Suppose you wanted to diff the
file you have on disk with something on the internet. Normally, you
would do:

.. code:: sh

    curl example.com/file.txt > tempfile.txt
    diff file.txt tempfile.txt
    rm tempfile.txt

But actually you can do:

.. code:: sh

    diff file.txt <(curl example.com/file.txt)

The ``<(command)`` syntax makes sh create a temporary file in /dev/fd/xxxx. This
is called Process Substitution.

The way you do the same with shalchemy is:

.. code:: python

    diff('file.txt', curl('example.com/file.txt').read_sub())

Once an expression's `read_sub` method is called, the result is a
ProcessSubstituteExpression which can no longer be composed with
other expressions. It can only be used as an argument directly to
other commands.

.. code:: python

    from io import StringIO
    from shalchemy import sh
    from shalchemy.bin import cat
    sh.run(cat < StringIO('my string'))

There is also a ``write_sub`` equivalent to sh's ``>(expr)``.

.. code:: python

    sh.run(
        cat('/usr/share/dict/words') |
        bin.tee(
            (cat > './words1.txt').write_sub(),
            (cat > './words2.txt').write_sub(),
        ) > '/dev/null'
    )
