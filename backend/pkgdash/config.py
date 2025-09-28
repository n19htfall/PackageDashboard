# configuration parsing of pkgdash
from dynaconf import Dynaconf

settings = Dynaconf(
    envvar_prefix="PKGDASH",
    settings_files=[
        "settings.toml",
        ".secrets.toml"
    ],
    environments=True,
    env_switcher="PKGDASH_ENV",
)

FRONTED_URL = "http://localhost:19429"

# `envvar_prefix` = export envvars with `export DYNACONF_FOO=bar`.
# `settings_files` = Load these files in the order.

if __name__ == '__main__':
    # test config
    print(dict(settings))
    print(settings.mongodb.url)