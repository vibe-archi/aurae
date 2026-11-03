#!/usr/bin/env bash
# Project-local first installation from the official public AURAE releases.
# Bash 3.2+, curl, unzip, and sha256sum or shasum; no package manager required.

aurae_usage() {
    cat <<'USAGE'
Usage: bash install.sh --agent codex|claude [--version X.Y.Z]

Run from the project root. Installs the latest published official AURAE release
under .agents/skills/aurae (Codex) or .claude/skills/aurae (Claude Code).
Use --version X.Y.Z or --version vX.Y.Z to select a published release.
Existing installations are never overwritten. Private distributions and upgrades
are not handled by this first-installation command.
USAGE
}

aurae_die() {
    printf 'AURAE installation refused: %s\n' "$*" >&2
    exit 1
}

aurae_cleanup() {
    # Both paths are unique directories allocated by this process with mktemp.
    # Never remove a project root, an existing installation, or a caller's path.
    if [[ -n ${AURAE_stage_dir:-} && ${AURAE_stage_dir%/*} == "$AURAE_skills_parent" &&
          ${AURAE_stage_dir##*/} == .aurae-install.* ]]; then
        if [[ -L $AURAE_agent_parent || -L $AURAE_skills_parent || -L $AURAE_stage_dir ]]; then
            printf 'Temporary cleanup skipped a changed linked installation path: %s\n' "$AURAE_stage_dir" >&2
        else
            rm -rf -- "$AURAE_stage_dir"
        fi
    fi
    if [[ -n ${AURAE_download_dir:-} && ${AURAE_download_dir%/*} == "$AURAE_temp_parent" &&
          ${AURAE_download_dir##*/} == aurae-download.* && ! -L $AURAE_download_dir ]]; then
        rm -rf -- "$AURAE_download_dir"
    fi
}

aurae_check_destination() {
    local path
    for path in "$AURAE_agent_parent" "$AURAE_skills_parent"; do
        [[ ! -L $path ]] || aurae_die "Destination ancestor is a symbolic link: $path"
        [[ ! -e $path || -d $path ]] || aurae_die "Destination ancestor is not a directory: $path"
    done
    [[ ! -e $AURAE_target && ! -L $AURAE_target ]] ||
        aurae_die "AURAE already exists at $AURAE_target. Use the documented upgrade procedure."
}

aurae_check_archive() {
    local zip=$1 prefix=$2 listing=$3 details=$4 entry_count mode_count=0
    local mode_re='^([-dlbcps?][rwxstST-]{9})[[:space:]]' line mode

    unzip -Z -1 "$zip" > "$listing" || aurae_die 'Cannot list the downloaded ZIP.'
    unzip -Z -l "$zip" > "$details" || aurae_die 'Cannot inspect ZIP entry types.'
    # One portable awk pass checks the entire path set, including case-insensitive
    # filesystems, without spawning a process for every path segment.
    if ! entry_count=$(awk -v prefix="$prefix" '
        function fail(message) { print message; failed = 1; exit 1 }
        {
            if (NR > 10000) fail("The ZIP exceeds the supported entry limit.")
            if (substr($0, 1, length(prefix)) != prefix ||
                $0 !~ /^[A-Za-z0-9._\/-]+$/ || length($0) > 240)
                fail("The ZIP contains an unexpected or non-portable path.")
            relative = substr($0, length(prefix) + 1)
            if (relative == "" || relative ~ /\/$/)
                fail("The ZIP must contain ordinary files, not directory entries.")
            if (relative in files) fail("The ZIP contains duplicate paths.")
            files[relative] = 1
            count = split(relative, parts, "/")
            cumulative = ""
            for (i = 1; i <= count; i++) {
                part = parts[i]
                if (part == "" || part == "." || part == ".." || part ~ /\.$/)
                    fail("The ZIP contains an unsafe path segment.")
                cumulative = (i > 1 ? cumulative "/" : "") part
                folded = tolower(cumulative)
                if (folded in spellings && spellings[folded] != cumulative)
                    fail("The ZIP contains case-colliding paths.")
                spellings[folded] = cumulative
            }
        }
        END {
            if (failed) exit 1
            if (NR == 0) fail("The ZIP is empty.")
            for (relative in files) {
                count = split(relative, parts, "/")
                cumulative = ""
                for (i = 1; i < count; i++) {
                    cumulative = (i > 1 ? cumulative "/" : "") parts[i]
                    if (cumulative in files) fail("The ZIP contains a file/directory collision.")
                }
            }
            if (!("SKILL.md" in files) || !("vendor.md" in files) || !("aurae-skill.yaml" in files))
                fail("The ZIP is missing a required package file.")
            print NR
        }
    ' "$listing"); then
        aurae_die "$entry_count"
    fi

    # Official builds contain Unix regular-file records only. In particular, do
    # not materialize ZIP symlinks. Counting records also detects split filenames.
    while IFS= read -r line || [[ -n $line ]]; do
        if [[ $line =~ $mode_re ]]; then
            mode=${BASH_REMATCH[1]}
            [[ ${mode:0:1} == - ]] || aurae_die 'The ZIP contains a non-regular file (for example a symbolic link).'
            mode_count=$((mode_count + 1))
        fi
    done < "$details"
    [[ $mode_count -eq $entry_count ]] || aurae_die 'ZIP entries do not match the official regular-file format.'

}

aurae_main() {
    set -euo pipefail
    export LC_ALL=C
    local agent='' version='' version_seen=0 resolved_url tag zip_name base_url
    local checksum_line digest='' checksum_count=0 calculated checksum_re entry relative
    local version_re='^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$'
    local latest_re='^https://github\.com/vibe-archi/aurae/releases/tag/v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$'
    local project prefix command

    while [[ $# -gt 0 ]]; do
        case $1 in
            --agent)
                [[ $# -ge 2 && -z $agent ]] || aurae_die '--agent requires one value and must appear once.'
                agent=$2; shift 2 ;;
            --version)
                [[ $# -ge 2 && $version_seen -eq 0 ]] || aurae_die '--version requires one value and must appear once.'
                version=$2; version_seen=1; shift 2 ;;
            --help|-h) aurae_usage; return 0 ;;
            *) aurae_die "Unknown argument: $1. Use --help." ;;
        esac
    done
    case $agent in
        codex) prefix='.agents/skills/aurae/' ;;
        claude) prefix='.claude/skills/aurae/' ;;
        *) aurae_die 'Choose --agent codex or --agent claude.' ;;
    esac
    if [[ $version_seen -eq 1 ]]; then
        version=${version#v}
        [[ $version =~ $version_re ]] || aurae_die 'Version must be X.Y.Z or vX.Y.Z (for example 1.19.0).'
    fi
    for command in curl unzip mktemp awk tr mv mkdir rm; do
        command -v "$command" >/dev/null 2>&1 || aurae_die "Required command not found: $command"
    done
    if command -v sha256sum >/dev/null 2>&1; then
        command=sha256sum
    elif command -v shasum >/dev/null 2>&1; then
        command=shasum
    else
        aurae_die 'Install sha256sum or shasum to verify package integrity.'
    fi

    project=$(pwd -P)
    AURAE_agent_parent="$project/${prefix%%/*}"
    AURAE_skills_parent="$AURAE_agent_parent/skills"
    AURAE_target="$AURAE_skills_parent/aurae"
    AURAE_download_dir=''
    AURAE_stage_dir=''
    aurae_check_destination

    # Resolve latest once, then fetch both assets from the same selected tag URL.
    if [[ $version_seen -eq 0 ]]; then
        resolved_url=$(curl -fLsS --connect-timeout 15 --max-time 120 --proto '=https' --proto-redir '=https' -o /dev/null -w '%{url_effective}' \
            'https://github.com/vibe-archi/aurae/releases/latest') || aurae_die 'Cannot find the latest published release.'
        [[ $resolved_url =~ $latest_re ]] || aurae_die 'Latest release did not resolve to an official vX.Y.Z release.'
        version=${resolved_url##*/v}
    fi
    tag="v$version"
    zip_name="aurae-$agent-$version.zip"
    base_url="https://github.com/vibe-archi/aurae/releases/download/$tag"
    AURAE_temp_parent=$(cd "${TMPDIR:-/tmp}" && pwd -P) || aurae_die 'Cannot access the system temporary directory.'
    AURAE_download_dir=$(mktemp -d "$AURAE_temp_parent/aurae-download.XXXXXXXX") || aurae_die 'Cannot allocate a download directory.'
    trap aurae_cleanup EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    printf 'Downloading AURAE %s for %s...\n' "$version" "$agent"
    curl -fLsS --connect-timeout 15 --max-time 120 --proto '=https' --proto-redir '=https' \
        --output "$AURAE_download_dir/$zip_name" "$base_url/$zip_name" || aurae_die 'Package download failed.'
    curl -fLsS --connect-timeout 15 --max-time 120 --proto '=https' --proto-redir '=https' \
        --output "$AURAE_download_dir/SHA256SUMS" "$base_url/SHA256SUMS" || aurae_die 'Checksum download failed.'

    checksum_re='^([[:xdigit:]]{64})  (.+)$'
    while IFS= read -r checksum_line || [[ -n $checksum_line ]]; do
        checksum_line=${checksum_line%$'\r'}
        if [[ $checksum_line =~ $checksum_re && ${BASH_REMATCH[2]} == "$zip_name" ]]; then
            digest=${BASH_REMATCH[1]}
            checksum_count=$((checksum_count + 1))
        fi
    done < "$AURAE_download_dir/SHA256SUMS"
    [[ $checksum_count -eq 1 ]] || aurae_die 'Missing or ambiguous exact package checksum.'
    if [[ $command == sha256sum ]]; then
        calculated=$(sha256sum "$AURAE_download_dir/$zip_name")
    else
        calculated=$(shasum -a 256 "$AURAE_download_dir/$zip_name")
    fi
    calculated=${calculated%% *}
    digest=$(printf '%s' "$digest" | tr '[:upper:]' '[:lower:]')
    [[ $calculated == "$digest" ]] || aurae_die 'Package checksum mismatch.'
    aurae_check_archive "$AURAE_download_dir/$zip_name" "$prefix" \
        "$AURAE_download_dir/entries" "$AURAE_download_dir/details"

    # All downloaded inputs are validated before creating project-local folders.
    aurae_check_destination
    mkdir -p -- "$AURAE_agent_parent"
    aurae_check_destination
    mkdir -p -- "$AURAE_skills_parent"
    aurae_check_destination
    AURAE_stage_dir=$(mktemp -d "$AURAE_skills_parent/.aurae-install.XXXXXXXX") || aurae_die 'Cannot allocate an installation stage.'
    mkdir -- "$AURAE_stage_dir/aurae"
    while IFS= read -r entry || [[ -n $entry ]]; do
        relative=${entry#"$prefix"}
        if [[ $relative == */* ]]; then
            mkdir -p -- "$AURAE_stage_dir/aurae/${relative%/*}"
        fi
        # Paths have no wildcard metacharacters. Stream only this exact ordinary
        # file into our fresh stage: unzip never chooses a destination or symlink.
        unzip -p "$AURAE_download_dir/$zip_name" "$entry" > "$AURAE_stage_dir/aurae/$relative" ||
            aurae_die "Could not extract package file: $relative"
    done < "$AURAE_download_dir/entries"
    for relative in SKILL.md vendor.md aurae-skill.yaml; do
        [[ -s $AURAE_stage_dir/aurae/$relative ]] || aurae_die "Required package file is empty: $relative"
    done
    aurae_check_destination
    # Pass the parent, not the final folder, as mv's destination. The staged name
    # is exactly aurae, so a concurrent installation is skipped, never nested.
    # Stage and target share a filesystem; promotion does not copy partial files.
    mv -n -- "$AURAE_stage_dir/aurae" "$AURAE_skills_parent/" || aurae_die 'Could not install the staged package.'
    [[ ! -e $AURAE_stage_dir/aurae && ! -L $AURAE_stage_dir/aurae ]] ||
        aurae_die 'The destination appeared during installation. It was not overwritten.'
    [[ -d $AURAE_target && ! -L $AURAE_target ]] || aurae_die 'Cannot verify the installed folder.'
    printf 'Installed AURAE %s locally at %s\n' "$version" "$AURAE_target"
    printf 'Review the installed skill and vendor profile, then start a new agent session.\n'
}

# Keep execution last so a truncated download cannot start a partial installer.
aurae_main "$@"
