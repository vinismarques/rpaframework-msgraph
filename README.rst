RPA Framework - MS Graph
========================

.. contents:: Table of Contents
    :local:
    :depth: 1

.. include-marker

Introduction
------------

`RPA Framework - MS Graph` is a standalone `Robot Framework`_ library made 
similarly to the `RPA Framework`_ project. It is standalone as an example
of how to build such libraries. The final code of this library will be 
included directly in that library, so updates should not be expected here.

Learn more about RPA at `Robocorp Documentation`_.

**The project is:**

- 100% Open Source
- Sponsored by `Robocorp`_
- Optimized for Robocorp `Control Room`_ and `Developer Tools`_
- Accepting external contributions

.. _Robot Framework: https://robotframework.org
.. _Robot Framework Foundation: https://robotframework.org/foundation/
.. _RPA Framework: https://github.com/robocorp/rpaframework
.. _Python: https://www.python.org/
.. _Robocorp: https://robocorp.com
.. _Robocorp Documentation: https://robocorp.com/docs/
.. _Control Room: https://robocorp.com/docs/control-room
.. _Developer Tools: https://robocorp.com/downloads
.. _Installing Python Packages: https://robocorp.com/docs/setup/installing-python-package-dependencies
.. _poetry: https://python-poetry.org
.. _invoke: https://www.pyinvoke.org
.. _Visual Studio Code: https://code.visualstudio.com
.. _GitHub: https://github.com/



Completion Challenge
--------------------

Robocorp is sponsoring an open challenge to the community to help complete this library!

In order to do so, you should fork this library and create your own branch based on ``main`` and
complete the code for the below list of keywords. Once you believe your code is ready, submit
a pull request back to this library on ``main`` and submit your information to the 
`Robocorp MSGraph Challenge form`_.

Grading will start on September 2, 2022 and will be graded in the order they are received. 
The winner is the first one to meet the following criteria:

- All keywords include documentation on use by a Robot developer, including examples
  in Robot Framework code.
- All keywords signatures and return values have type hints.
- All keywords return the appropriate type or execute the appropriate change in state.
- All keywords are tested either via a ``pytest`` unit test or a robot test.
- Code passes all linting checks (hint: run ``invoke lint`` before you create
  a pull request!).
- Code is formatted with ``black``.

.. _Robocorp MSGraph Challenge form: https://robocorp.typeform.com/to/xGNs03v5

Keywords Required
^^^^^^^^^^^^^^^^^

- ``List files in OneDrive folder``
- ``Download file from OneDrive``
- ``Find OneDrive file``
- ``Download OneDrive file from share link``
- ``Upload file to OneDrive``
- ``Get Sharepoint site``
- ``Get Sharepoint list``
- ``Create Sharepoint list``
- ``List Sharepoint site drives``
- ``List files in Sharepoint site drive``
- ``Download file from Sharepoint``

Stretch Goals
^^^^^^^^^^^^^

The following keywords are not required to win the competition, but they are in need:

- ``List calendars``
- ``List calendar events``
- ``Get calendar event``
- ``Create new calendar event``

Installing The Developer Environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In order to work on this library, you will need to install the developer environment.
Luckily, with the help of `poetry`_ and `invoke`_, it should be relatively straight forward.

Follow these steps to get your `Visual Studio Code`_ environment up and
running (these steps were generated from a Windows machine inside Visual Studio Code
termainal, for other IDEs and operating systems, you may need to find alternate tutorials):

#. Fork this library on `GitHub`_.
#. Install `Python`_ on your machine, we strongly recommend ``v3.9.13``.
#. Use pip to install global copies of ``poetry``, ``invoke``, and ``toml`` from an elevated 
   terminal into your v3.9.13 installation of Python (you may need to activate the proper
   Python installation before performing this install if you have multiple Python versions
   installed).

.. code:: shell

   pip install poetry invoke toml

#. Clone your forked library locally.
#. Execute the following ``invoke`` command from the root of the repository in your filesystem, 
   which should install the development environment in a local ``.venv`` folder within your 
   repository.

.. code:: shell
   
   invoke setup-poetry install

#. Open a ``*.py`` file and double check that VSCode is using the correct python interpreter
   from the ``.venv`` folder.
#. Run Python unit tests with ``invoke test-python``.

Installation For Robot Developers
---------------------------------

Learn about installing Python packages at `Installing Python Packages`_.

Default installation method with Robocorp `Developer Tools`_ using conda.yaml:

.. code-block:: yaml

   channels:
     - conda-forge
   dependencies:
     - python=3.9.13
     - pip=22.1.2
     - pip:
       - rpaframework==15.5.0
       - rpaframework-msgraph==0.1.0


Example
-------

After installation the libraries can be directly imported inside
`Robot Framework`_:

.. code:: robotframework

    *** Settings ***
    Library    RPA.MSGraph

    *** Tasks ***
    Login as user
        Authorize MS Graph Client    client_id=<id-here>    client_secret=<secret-here>

The libraries are also available inside Python_:

.. code:: python

    from RPA.MSGraph import MSGraph

    lib = MSGraph()

    lib.authorize_client("<id-here>","<secret-here>")

