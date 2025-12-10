# PackageDashboard
Package Dashboard: A cross-ecosystem Software Composition Analysis (SCA) tool that provides a unified view of supply chain risk by analyzing both software artifacts and upstream community health.

## Installation

### System Requirements

Package Dashboard is a web application with both a frontend and a backend. Before installing, please ensure the following components are present on your device:

1. Ubuntu 22.04
2. Python 3.10
3. npm
4. MongoDB


### Backend

Package Dashboard depends on scancode-toolkit for operation. Ensure that [scancode-toolkit](https://scancode-toolkit.readthedocs.io/en/stable/getting-started/install.html#source-code-install) is present on your system.

We recommend using a Python virtual environment.

```bash
cd ./backend
python -m venv venv
```

We use `Poetry` to manage dependencies:

1. Install `pipx` first, see [documentation](https://pipx.pypa.io/stable/installation/)

2. Install `Poetry`
```bash
pipx install poetry
```

3. Install project dependencies from the `poetry.lock` file.
```bash
source ./backend/venv/bin/activate
poetry install
```

This project relies on Ubuntu Packages for dependency resolution.

``` bash
apt install libsolv1 libapt-pkg-dev
```

### Frontend

We use `pnpm` to manage frontend dependencies:

1. Install `pnpm`
```bash
npm install -g pnpm
```

2. Install project dependencies.

```bash
cd ./frontend
pnpm install
```

## Running

1. Backend
```bash
poetry run python -m pkgdash.serve
```

2. Frontend
```bash
pnpm run dev
```