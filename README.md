# workflows

Welcome to your new Dagster repository.


## Pre requirements

1. Install [poetry](https://python-poetry.org/docs/)

## Getting up and running

1. Create a new Python environment and activate.

**Pyenv**
```bash
export PYTHON_VERSION=X.Y.Z
pyenv install $PYTHON_VERSION
pyenv virtualenv $PYTHON_VERSION workflows
pyenv activate workflows
```


2. Once you have activated your Python environment, install your repository as a Python package.

```bash
poetry install
```

## Local Development

1. Set the `DAGSTER_HOME` environment variable. Dagster will store run history in this directory.

```base
mkdir ~/dagster_home
export DAGSTER_HOME=~/dagster_home
```

2. Start the [Dagit process](https://docs.dagster.io/overview/dagit). This will start a Dagit web
server that, by default, is served on http://localhost:3000.

```bash
poetry run dagit
```

3. Start running with [Dagster CLI](https://docs.dagster.io/concepts/modes-resources#dagster-cli). In preset, the [mode](https://github.com/ErnestaP/workflows-1/blob/master/workflows/pipelines/my_pipeline.py#L18-L43) has to be set.

```bash
poetry run dagster pipeline execute -f workflows/pipelines/my_pipeline.py --preset <preset you want to run>
```

4. (Optional) If you want to enable Dagster
[Schedules](https://docs.dagster.io/overview/schedules-sensors/schedules) or
[Sensors](https://docs.dagster.io/overview/schedules-sensors/sensors) for your pipelines, start the
[Dagster Daemon process](https://docs.dagster.io/overview/daemon#main) **in a different shell or terminal**:

```bash
poetry run dagster-daemon run
```

## Local Testing

Tests can be found in `workflows_tests` and are run with the following command:

```bash
poetry run pytest workflows_tests
```

As you create Dagster solids and pipelines, add tests in `workflows_tests/` to check that your
code behaves as desired and does not break over time.

[For hints on how to write tests for solids and pipelines in Dagster,
[see our documentation tutorial on Testing](https://docs.dagster.io/tutorial/testable).
