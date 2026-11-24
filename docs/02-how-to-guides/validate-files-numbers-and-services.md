# How to Validate Files, Numbers, and Services

Use this procedure to execute `is.sh` checks inside Bash automation scripts cleanly.

## Prerequisites

- Confirm Bash and GNU `stat`, `awk`, and `grep` are installed on the Linux host.
- Confirm file paths with spaces stay outside `fsize`, `fsizelt`, and `fsizegt` calls.

NOTE: Review all predicate names, aliases, and GNU limits in [Predicates, Aliases, and Caveats Reference](../03-reference/predicates-aliases-and-caveats.md).

## Procedure

### Load `is.sh` Safely in Scripts

CAUTION: Invoke `--help` and `--version` only via `./is.sh` subcommands. Sourced `is --help` calls `exit` and terminates your parent shell.

1. Source `is.sh` inside your Bash script or run `./is.sh` per check:

```bash
source ./is.sh
```

2. Validate target paths and byte limits before file access:

```bash
is file ./is.sh && is executable ./is.sh
is fsizegt ./is.sh 0 && is user "$(whoami)"
```

3. Validate numeric thresholds and regex patterns with `not` when required:

```bash
is number "42" && is not lt "42" "10"
is matching '^[0-9]+$' "42"
```

## Validation

Run both the shell predicate suite and the Python test suite:

```bash
bash tests/tests.sh
python3 -m unittest discover -s tests -p "test_*.py" -v
```

Confirm both test suites exit with status code `0`.

## Rollback

If sourced functions pollute your active Bash environment, remove `is` cleanly:

```bash
unset -f is
```

Read dispatch mechanics and portability context in [Recursive Dispatch and Portability](../04-explanation/recursive-dispatch-and-portability.md).
