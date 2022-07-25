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
.. _Python: https://www.python.org/
.. _Robocorp: https://robocorp.com
.. _Robocorp Documentation: https://robocorp.com/docs/
.. _Control Room: https://robocorp.com/docs/control-room
.. _Developer Tools: https://robocorp.com/downloads
.. _Installing Python Packages: https://robocorp.com/docs/setup/installing-python-package-dependencies

Installation
------------

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

