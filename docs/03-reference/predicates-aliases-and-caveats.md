# Predicates, Aliases, and Caveats Reference

Exact behavior implemented in `is.sh` (`161` lines, tag `v1.1.2`), `package.json`, and `tests/`.

## CLI Options and Modifiers

| Token | Role | Behavior |
| :--- | :--- | :--- |
| `--help` | Usage printout | Prints conditions list and calls `exit` |
| `--version` | Version printout | Prints `is.sh 1.1.0` (`is.sh:L57`) and calls `exit` (`package.json` = `1.1.2`) |
| `not` | Prefix modifier | Strips `not` (`shift 1`) and returns negated exit status (`! is "$@"`) |
| `a`, `an`, `the` | Article sugar | Strips one leading article (`shift 1`) and dispatches recursively |

## Conditions Matrix (`case "$condition"`)

| Condition | Aliases | Arguments | Underlying Check / Requirement |
| :--- | :--- | :--- | :--- |
| `equal` | `eq` | `<A> <B>` | String `[ "$value_a" = "$value_b" ]` or numeric `awk` `==` |
| `gt`, `lt`, `ge`, `le` | — | `<N1> <N2>` | Rejects non-numbers (`is not a number`), compares via `awk` |
| `matching` | `match` | `<REGEXP> <VAL>` | `echo "$value_b" \| grep -xE "$value_a"` |
| `substring` | `substr` | `<NEEDLE> <HAY>` | `echo "$value_b" \| grep -F "$value_a"` |
| `empty` | — | `<VAL>` | `[ -z "$value_a" ]` |
| `number` | — | `<VAL>` | Regex `^[0-9]+(\.[0-9]+)?$` (`grep -E`, unsigned only) |
| `true` / `false` | — | `<VAL>` | `true` matches `"true"` or `"0"`; `false` is logical complement |
| `file`, `dir`, `link` | `directory`, `symlink` | `<PATH>` | POSIX `[ -f ]`, `[ -d ]`, `[ -L ]` |
| `existent` | `existing`, `exist`, `exists` | `<PATH>` | `[ -e "$value_a" ]` |
| `readable`, `writeable`, `executable` | — | `<PATH>` | `[ -r ]`, `[ -w ]`, `[ -x ]` |
| `older`, `newer` | — | `<PATH_A> <PATH_B>` | `[ "$value_a" -ot / -nt "$value_b" ]` |
| `available` | `installed` | `<CMD>` | `which "$value_a"` |
| `fowner`, `fgroup`, `fmountpoint` | `fuser` -> `fowner` | `<PATH> <EXPECTED>` | Linux GNU `stat -c %U` / `%G` / `%m` (`fuser` requires 2 args) |
| `fempty` | — | `<PATH>` | Linux GNU `stat -c %s` equals `"0"` |
| `fsize`, `fsizelt`, `fsizegt` | — | `<PATH> <BYTES>` | Unquoted `[ $(stat -c %s $value_a) ... $value_b ]` |
| `forights` | — | `<PATH> <OCTAL>` | Linux GNU `stat -c %a` |
| `user` | — | `<USER>` | Calls `is eq $(whoami) $value_a` |
| `tcp_port` | `tport`, `tcp_port_open` | `<PORT>` | `netstat -ltn \| grep -E ":${value_a}\s" \| grep -q 'LISTEN'` |

## Known Caveats

| Item | Location | Verified Details |
| :--- | :--- | :--- |
| `--help` heredoc `$path` | `is.sh:L39-40` | Unescaped `$path` expands inside heredoc (`PATH$path` -> `PATH`) |
| `fuser` vs `user` | `is.sh:L42,96,112` | `--help` lists `is fuser USER`, but `fuser` aliases 2-arg `fowner`; current user check is `is user <USER>` |
| Version string lag | `is.sh:L57` vs `package.json:L3` | `--version` prints `1.1.0` while `package.json` and tag are `1.1.2` |
| GNU `stat -c` & unquoted path | `is.sh:L97-111` | Fails on BSD/macOS without GNU `stat` (note `8ccfc22` removed `gstat` wrapper) and breaks on spaces in `fsize*` paths |
| Interactive `exit` | `is.sh:L53,58` | `--help` and `--version` call `exit` directly instead of `return 0`, closing a sourced shell |
