from __future__ import annotations
import os
import re
import sys
from importlib.metadata import PackageNotFoundError, metadata
from itertools import chain
from pathlib import Path
from textwrap import dedent
from typing import Any  # Removed 'Mapping' import as it is not used

from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

# Support for Python 3.11+
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

# Define project directories and load configuration
project_dir = Path(os.getenv("MKDOCS_CONFIG_DIR", "."))
with project_dir.joinpath("pyproject.toml").open("rb") as pyproject_file:
    pyproject = tomllib.load(pyproject_file)
project = pyproject.get("project", {})
pdm = pyproject.get("tool", {}).get("pdm", {})
with project_dir.joinpath("pdm.lock").open("rb") as lock_file:
    lock_data = tomllib.load(lock_file)

# Lock package data
lock_pkgs = {pkg["name"].lower(): pkg for pkg in lock_data["package"]}

# Regular expression to parse package dependency information
regex = re.compile(r"(?P<dist>[\w.-]+)(?P<spec>.*)$")

def _get_license(pkg_name: str) -> str:
    """Fetch the license of a package from its metadata."""
    try:
        data = metadata(pkg_name)
    except PackageNotFoundError:
        return "?"
    license_name = data.get("License", "").strip()
    if not license_name or license_name == "UNKNOWN":
        for header, value in data.items():
            if header == "Classifier" and value.startswith("License ::"):
                license_name = value.rsplit("::", 1)[1].strip()
    return license_name or "?"


def _get_deps(base_deps: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Process dependencies and return details about each one."""
    deps: dict[str, dict[str, Any]] = {}
    for dep in base_deps:
        parsed = regex.match(dep)
        if not parsed:
            continue
        dep_name = parsed.group("dist").lower()
        if dep_name not in lock_pkgs:
            continue
        deps[dep_name] = {
            "license": _get_license(dep_name),
            **parsed.groupdict(),
            **lock_pkgs[dep_name],
        }

    again = True
    while again:
        again = False
        for pkg_name, pkg_data in lock_pkgs.items():
            if pkg_name in deps:
                for pkg_dependency in pkg_data.get("dependencies", []):
                    parsed = regex.match(pkg_dependency)
                    if not parsed:
                        continue
                    dep_name = parsed.group("dist").lower()
                    if dep_name in lock_pkgs and dep_name not in deps and dep_name != project.get("name"):
                        deps[dep_name] = {
                            "license": _get_license(dep_name),
                            **parsed.groupdict(),
                            **lock_pkgs[dep_name],
                        }
                        again = True

    return deps


def _render_credits() -> str:
    """Render and generate the credit page for the project."""
    dev_dependencies = _get_deps(chain(*pdm.get("dev-dependencies", {}).values()))
    prod_dependencies = _get_deps(
        chain(
            project.get("dependencies", []),
            chain(*project.get("optional-dependencies", {}).values()),
        ),
    )

    template_data = {
        "project_name": project.get("name", ""),
        "prod_dependencies": sorted(prod_dependencies.values(), key=lambda dep: dep["name"]),
        "dev_dependencies": sorted(dev_dependencies.values(), key=lambda dep: dep["name"]),
        "more_credits": "",  # Placeholder for any additional credits
    }

    template_text = dedent("""\
        # Credits

        These projects were used to build *{{ project_name }}*. **Thank you!**

        [python](https://www.python.org/) |
        [pdm](https://pdm.fming.dev/) |
        [copier-pdm](https://github.com/pawamoy/copier-pdm)

        {% macro dep_line(dep) -%}
        [{{ dep.name }}](https://pypi.org/project/{{ dep.name }}/) | {{ dep.summary }} | {{ ("" ~ dep.spec ~ "") if dep.spec else "" }} | {{ dep.version }} | {{ dep.license }}
        {%- endmacro %}

        ### Runtime dependencies

        Project | Summary | Version (accepted) | Version (last resolved) | License
        ------- | ------- | ------------------ | ----------------------- | -------
        {% for dep in prod_dependencies -%}
        {{ dep_line(dep) }}
        {% endfor %}

        ### Development dependencies

        Project | Summary | Version (accepted) | Version (last resolved) | License
        ------- | ------- | ------------------ | ----------------------- | -------
        {% for dep in dev_dependencies -%}
        {{ dep_line(dep) }}
        {% endfor %}

        {% if more_credits %}**[More credits from the author]({{ more_credits }})**{% endif %}
    """)

    jinja_env = SandboxedEnvironment(undefined=StrictUndefined)
    return jinja_env.from_string(template_text).render(**template_data)


# Print out the generated credits
print(_render_credits())
