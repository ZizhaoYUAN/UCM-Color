UCM Color Admin Installer
=========================

This bundle contains everything required to install the packaged
backend service. Each archive ships with the following files:

- ``ucm_color_admin-*.whl`` – Python wheel containing the backend code.
- ``install.sh`` – shell installer for Linux and macOS.
- ``install.ps1`` – PowerShell installer for Windows.

Install steps
-------------

Linux/macOS::

    chmod +x install.sh
    ./install.sh /desired/install/path

Windows (PowerShell)::

    powershell -ExecutionPolicy Bypass -File install.ps1 -InstallDir "C:\\UCMColorAdmin"

Once installed, use the generated launcher script to manage the
service. For example::

    /desired/install/path/ucm-color-admin.sh run

or on Windows::

    powershell -File C:\\UCMColorAdmin\\ucm-color-admin.ps1 run

The CLI exposes helpers to initialise the database and create
administrators::

    ucm-color-admin init-db
    ucm-color-admin create-admin admin

Refer to the project README for detailed documentation.
