"""What the commands in `tools/` are built from.

A module here is imported and never run. A module one directory up is run and
never imported, so that which of the two a file is can be told from where it
sits rather than from reading it. The one shape that would blur the two, a
command another command imports, is split instead: the work lands here and the
command above keeps only its argument parsing.
"""
