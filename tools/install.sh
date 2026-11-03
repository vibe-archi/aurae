#!/usr/bin/env bash
# Project-local installation and verified updates from official public releases.
# Bash 3.2+, curl, unzip, and sha256sum or shasum; no package manager required.

aurae_usage() {
    cat <<'USAGE'
Usage: bash install.sh --agent codex|claude [--version X.Y.Z] [--update]

Run from the project root. Installs the latest published official AURAE release
under .agents/skills/aurae (Codex) or .claude/skills/aurae (Claude Code).
Use --version X.Y.Z or --version vX.Y.Z to select a published release.
Without --update, existing installations are never overwritten. With --update,
only an unchanged official installation can be replaced by a newer release.
Modified/private installations and downgrades are refused. A verified backup is
kept outside the project under ${XDG_STATE_HOME:-$HOME/.local/state}/aurae/skill-backups.
Close or pause agents using the skill before updating; restart them afterwards.
USAGE
}

aurae_die() {
    printf 'AURAE installation refused: %s\n' "$*" >&2
    exit 1
}

aurae_cleanup() {
    # Both paths are unique directories allocated by this process with mktemp.
    # Never remove a project root, an existing installation, or a caller's path.
    if [[ ${AURAE_old_moved:-0} -eq 1 && ${AURAE_update_succeeded:-0} -eq 0 ]]; then
        aurae_rollback || true
    fi
    if [[ ${AURAE_preserve_stage:-0} -eq 0 && -n ${AURAE_stage_dir:-} && ${AURAE_stage_dir%/*} == "$AURAE_skills_parent" &&
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

aurae_check_parents() {
    local path
    for path in "$AURAE_agent_parent" "$AURAE_skills_parent"; do
        [[ ! -L $path ]] || aurae_die "Destination ancestor is a symbolic link: $path"
        [[ ! -e $path || -d $path ]] || aurae_die "Destination ancestor is not a directory: $path"
    done
}

aurae_check_destination() {
    aurae_check_parents
    if [[ ${AURAE_update:-0} -eq 1 ]]; then
        [[ -d $AURAE_target && ! -L $AURAE_target ]] ||
            aurae_die "--update requires an existing non-linked skill directory at $AURAE_target."
    else
        [[ ! -e $AURAE_target && ! -L $AURAE_target ]] ||
            aurae_die "AURAE already exists at $AURAE_target. Use --update for an unchanged official installation."
    fi
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

aurae_hash() {
    local calculated
    if [[ $AURAE_hash_command == sha256sum ]]; then
        calculated=$(sha256sum "$1")
    else
        calculated=$(shasum -a 256 "$1")
    fi
    printf '%s\n' "${calculated%% *}"
}

aurae_download_package() {
    local version=$1 agent=$2 prefix=$3 directory=$4
    local zip_name="aurae-$agent-$version.zip"
    local base_url="https://github.com/vibe-archi/aurae/releases/download/v$version"
    local checksum_re='^([[:xdigit:]]{64})  (.+)$' checksum_line digest='' checksum_count=0
    mkdir -- "$directory"
    printf 'Downloading AURAE %s for %s...\n' "$version" "$agent"
    curl -fLsS --connect-timeout 15 --max-time 120 --proto '=https' --proto-redir '=https' \
        --output "$directory/$zip_name" "$base_url/$zip_name" || aurae_die 'Package download failed.'
    curl -fLsS --connect-timeout 15 --max-time 120 --proto '=https' --proto-redir '=https' \
        --output "$directory/SHA256SUMS" "$base_url/SHA256SUMS" || aurae_die 'Checksum download failed.'
    while IFS= read -r checksum_line || [[ -n $checksum_line ]]; do
        checksum_line=${checksum_line%$'\r'}
        if [[ $checksum_line =~ $checksum_re && ${BASH_REMATCH[2]} == "$zip_name" ]]; then
            digest=${BASH_REMATCH[1]}
            checksum_count=$((checksum_count + 1))
        fi
    done < "$directory/SHA256SUMS"
    [[ $checksum_count -eq 1 ]] || aurae_die 'Missing or ambiguous exact package checksum.'
    digest=$(printf '%s' "$digest" | tr '[:upper:]' '[:lower:]')
    [[ $(aurae_hash "$directory/$zip_name") == "$digest" ]] || aurae_die 'Package checksum mismatch.'
    aurae_check_archive "$directory/$zip_name" "$prefix" "$directory/entries" "$directory/details"
}

aurae_extract_package() {
    local zip=$1 prefix=$2 listing=$3 stage=$4 entry relative
    mkdir -- "$stage"
    while IFS= read -r entry || [[ -n $entry ]]; do
        relative=${entry#"$prefix"}
        if [[ $relative == */* ]]; then mkdir -p -- "$stage/${relative%/*}"; fi
        # No wildcard metacharacters are allowed. unzip never chooses a pathname.
        unzip -p "$zip" "$entry" > "$stage/$relative" || aurae_die "Could not extract package file: $relative"
    done < "$listing"
    for relative in SKILL.md vendor.md aurae-skill.yaml; do
        [[ -s $stage/$relative ]] || aurae_die "Required package file is empty: $relative"
    done
}

aurae_installed_version() {
    local manifest=$1 line found='' count=0
    local version_re='^agent_skill: ((0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*))$'
    [[ -f $manifest && ! -L $manifest ]] || aurae_die 'The installed skill has no regular generated manifest; update it manually.'
    while IFS= read -r line || [[ -n $line ]]; do
        if [[ $line == agent_skill:* ]]; then
            [[ $line =~ $version_re ]] || aurae_die 'The installed version is not in the supported generated-manifest format.'
            found=${BASH_REMATCH[1]}
            count=$((count + 1))
        fi
    done < "$manifest"
    [[ $count -eq 1 ]] || aurae_die 'The installed manifest must contain exactly one agent_skill version.'
    printf '%s\n' "$found"
}

aurae_version_order() {
    # Compare decimal components as strings, without numeric overflow or octal.
    local -a left right
    local index
    IFS=. read -r -a left <<< "$1"
    IFS=. read -r -a right <<< "$2"
    for index in 0 1 2; do
        if [[ ${#left[index]} -lt ${#right[index]} ]]; then printf '%s\n' -1; return; fi
        if [[ ${#left[index]} -gt ${#right[index]} ]]; then printf '%s\n' 1; return; fi
        if [[ ${left[index]} < ${right[index]} ]]; then printf '%s\n' -1; return; fi
        if [[ ${left[index]} > ${right[index]} ]]; then printf '%s\n' 1; return; fi
    done
    printf '%s\n' 0
}

aurae_check_tree() {
    local tree=$1 reference=$2 unusual
    [[ -d $tree && ! -L $tree ]] || aurae_die 'The installed skill directory changed or is linked.'
    unusual=$(find "$tree" ! -type d ! -type f -print) || aurae_die 'Cannot inspect the installed skill.'
    [[ -z $unusual ]] || aurae_die 'The installed skill contains links or special entries; preserve it and update manually.'
    diff -r -- "$reference" "$tree" >/dev/null 2>&1 ||
        aurae_die 'The installed skill differs from its verified official release (modified, private, extra or missing content). Nothing will be overwritten.'
}

aurae_check_backup_path() {
    local path=$1 current='' part
    local -a pieces
    [[ $path == /* && ! $path =~ [[:cntrl:]] ]] || aurae_die 'The backup state directory must be an absolute path without control characters.'
    IFS=/ read -r -a pieces <<< "$path"
    for part in "${pieces[@]}"; do
        [[ -n $part ]] || continue
        [[ $part != . && $part != .. ]] || aurae_die 'The backup state directory cannot contain dot segments.'
        current="$current/$part"
        [[ ! -L $current && ( ! -e $current || -d $current ) ]] ||
            aurae_die "Unsafe backup directory ancestor: $current"
    done
}

aurae_make_backup() {
    local old_zip=$1 old_version=$2 new_version=$3 prefix=$4 project=$5
    local state_root="${XDG_STATE_HOME:-$HOME/.local/state}" base folded_base folded_project cursor digest
    base="${state_root%/}/aurae/skill-backups"
    aurae_check_backup_path "$base"
    folded_base=$(printf '%s' "$base" | tr '[:upper:]' '[:lower:]')
    folded_project=$(printf '%s' "$project" | tr '[:upper:]' '[:lower:]')
    case "$folded_base/" in
        "$folded_project/"*|*/.agents/skills/*|*/.claude/skills/*|*/.codex/skills/*)
            aurae_die 'The backup location must be outside this project and all agent skill directories; choose another XDG_STATE_HOME.' ;;
    esac
    # Identity checks also catch alternate casing of non-ASCII project names on
    # case-insensitive filesystems, without assuming shell case folding is Unicode.
    cursor=$base
    while :; do
        [[ ! -e $cursor || ! $cursor -ef $project ]] || aurae_die 'The backup location is inside this project.'
        [[ $cursor != / ]] || break
        cursor=${cursor%/*}
        [[ -n $cursor ]] || cursor=/
    done
    mkdir -p -- "$base"
    aurae_check_backup_path "$base"
    base=$(cd "$base" && pwd -P)
    folded_base=$(printf '%s' "$base" | tr '[:upper:]' '[:lower:]')
    case "$folded_base/" in
        "$folded_project/"*|*/.agents/skills/*|*/.claude/skills/*|*/.codex/skills/*)
            aurae_die 'The resolved backup location is inside the project or an agent skill directory.' ;;
    esac
    AURAE_backup_dir=$(mktemp -d "$base/aurae-$old_version.XXXXXXXX") || aurae_die 'Cannot create a durable backup directory.'
    cp -- "$old_zip" "$AURAE_backup_dir/skill.zip" || aurae_die 'Cannot save the verified previous release.'
    digest=$(aurae_hash "$old_zip")
    [[ $digest == "$(aurae_hash "$AURAE_backup_dir/skill.zip")" ]] || aurae_die 'Backup verification failed.'
    {
        printf 'AURAE official skill update backup\n\nProject: %s\nDestination: %s\n' "$project" "$AURAE_target"
        printf 'Previous version: %s\nRequested version: %s\nZIP prefix: %s\n' "$old_version" "$new_version" "$prefix"
        printf 'skill.zip SHA-256: %s\n' "$digest"
        printf '\nThe previous installation matched this official ZIP byte for byte.\n'
        printf 'To restore: pause agents, preserve the current skill folder separately,\n'
        printf 'then extract skill.zip at the project root ONLY when the destination is absent.\n'
        printf 'Do not overlay either installation. Restart the agent afterwards.\n'
    } > "$AURAE_backup_dir/restore-info.txt" || aurae_die 'Cannot write backup recovery instructions.'
    printf 'Verified backup retained at %s\n' "$AURAE_backup_dir"
}

aurae_rollback() {
    local previous="$AURAE_stage_dir/previous/aurae"
    # A failed move can leave the original untouched. Never replace an occupant.
    if [[ ! -e $previous && ! -L $previous ]]; then return 0; fi
    if [[ ! -L $AURAE_agent_parent && ! -L $AURAE_skills_parent && ! -L $AURAE_stage_dir &&
          -d $previous && ! -L $previous && ! -e $AURAE_target && ! -L $AURAE_target ]]; then
        if mv -n -- "$previous" "$AURAE_skills_parent/" && [[ ! -e $previous && ! -L $previous ]]; then
            printf 'The update did not complete; the previous installation was restored.\n' >&2
            return 0
        fi
    fi
    AURAE_preserve_stage=1
    printf 'Automatic restore was blocked; no existing destination was overwritten.\nPrevious tree retained at %s\nVerified backup: %s\n' \
        "$previous" "${AURAE_backup_dir:-unavailable}" >&2
    return 1
}

aurae_main() {
    set -euo pipefail
    export LC_ALL=C
    local agent='' version='' version_seen=0 resolved_url zip_name installed_version='' order=''
    local version_re='^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$'
    local latest_re='^https://github\.com/vibe-archi/aurae/releases/tag/v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$'
    local project prefix command new_directory old_directory old_zip=''
    AURAE_update=0

    while [[ $# -gt 0 ]]; do
        case $1 in
            --agent)
                [[ $# -ge 2 && -z $agent ]] || aurae_die '--agent requires one value and must appear once.'
                agent=$2; shift 2 ;;
            --version)
                [[ $# -ge 2 && $version_seen -eq 0 ]] || aurae_die '--version requires one value and must appear once.'
                version=$2; version_seen=1; shift 2 ;;
            --update)
                [[ $AURAE_update -eq 0 ]] || aurae_die '--update must appear once.'
                AURAE_update=1; shift ;;
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
        AURAE_hash_command=sha256sum
    elif command -v shasum >/dev/null 2>&1; then
        AURAE_hash_command=shasum
    else
        aurae_die 'Install sha256sum or shasum to verify package integrity.'
    fi

    project=$(pwd -P)
    AURAE_agent_parent="$project/${prefix%%/*}"
    AURAE_skills_parent="$AURAE_agent_parent/skills"
    AURAE_target="$AURAE_skills_parent/aurae"
    AURAE_download_dir=''
    AURAE_stage_dir=''
    AURAE_backup_dir=''
    AURAE_old_moved=0
    AURAE_update_succeeded=0
    AURAE_preserve_stage=0
    aurae_check_destination
    if [[ $AURAE_update -eq 1 ]]; then
        for command in find diff cp; do
            command -v "$command" >/dev/null 2>&1 || aurae_die "Required update command not found: $command"
        done
        installed_version=$(aurae_installed_version "$AURAE_target/aurae-skill.yaml")
    fi

    # Resolve latest once, then fetch both assets from the same selected tag URL.
    if [[ $version_seen -eq 0 ]]; then
        resolved_url=$(curl -fLsS --connect-timeout 15 --max-time 120 --proto '=https' --proto-redir '=https' -o /dev/null -w '%{url_effective}' \
            'https://github.com/vibe-archi/aurae/releases/latest') || aurae_die 'Cannot find the latest published release.'
        [[ $resolved_url =~ $latest_re ]] || aurae_die 'Latest release did not resolve to an official vX.Y.Z release.'
        version=${resolved_url##*/v}
    fi
    zip_name="aurae-$agent-$version.zip"
    if [[ $AURAE_update -eq 1 ]]; then
        order=$(aurae_version_order "$version" "$installed_version")
        [[ $order != -1 ]] || aurae_die "Downgrades are not supported: installed $installed_version, requested $version."
    fi
    AURAE_temp_parent=$(cd "${TMPDIR:-/tmp}" && pwd -P) || aurae_die 'Cannot access the system temporary directory.'
    AURAE_download_dir=$(mktemp -d "$AURAE_temp_parent/aurae-download.XXXXXXXX") || aurae_die 'Cannot allocate a download directory.'
    trap aurae_cleanup EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    if [[ $AURAE_update -eq 1 ]]; then
        old_directory="$AURAE_download_dir/previous-release"
        old_zip="$old_directory/aurae-$agent-$installed_version.zip"
        aurae_download_package "$installed_version" "$agent" "$prefix" "$old_directory"
        aurae_extract_package "$old_zip" "$prefix" "$old_directory/entries" "$old_directory/reference"
        [[ $(aurae_installed_version "$old_directory/reference/aurae-skill.yaml") == "$installed_version" ]] ||
            aurae_die 'The previous release archive does not match its requested version.'
        aurae_check_destination
        aurae_check_tree "$AURAE_target" "$old_directory/reference"
        if [[ $order == 0 ]]; then
            printf 'AURAE %s is already installed and matches the verified official release. No changes made.\n' "$version"
            return 0
        fi
    fi
    new_directory="$AURAE_download_dir/requested-release"
    aurae_download_package "$version" "$agent" "$prefix" "$new_directory"

    # All downloaded inputs are validated before creating project-local folders.
    aurae_check_destination
    mkdir -p -- "$AURAE_agent_parent"
    aurae_check_destination
    mkdir -p -- "$AURAE_skills_parent"
    aurae_check_destination
    AURAE_stage_dir=$(mktemp -d "$AURAE_skills_parent/.aurae-install.XXXXXXXX") || aurae_die 'Cannot allocate an installation stage.'
    aurae_extract_package "$new_directory/$zip_name" "$prefix" "$new_directory/entries" "$AURAE_stage_dir/aurae"
    [[ $(aurae_installed_version "$AURAE_stage_dir/aurae/aurae-skill.yaml") == "$version" ]] ||
        aurae_die 'The requested archive does not match its release version.'
    if [[ $AURAE_update -eq 1 ]]; then
        aurae_make_backup "$old_zip" "$installed_version" "$version" "$prefix" "$project"
    fi
    aurae_check_destination
    if [[ $AURAE_update -eq 1 ]]; then
        # Check again immediately before mutation, then again after moving the
        # original: edits made while downloads ran must never be silently lost.
        aurae_check_tree "$AURAE_target" "$old_directory/reference"
        mkdir -- "$AURAE_stage_dir/previous"
        AURAE_old_moved=1
        mv -n -- "$AURAE_target" "$AURAE_stage_dir/previous/" || aurae_die 'Could not preserve the previous skill for replacement.'
        [[ -d $AURAE_stage_dir/previous/aurae && ! -e $AURAE_target && ! -L $AURAE_target ]] ||
            aurae_die 'The destination changed during replacement; the new skill was not installed.'
        aurae_check_tree "$AURAE_stage_dir/previous/aurae" "$old_directory/reference"
        aurae_check_parents
    fi
    # Pass the parent, not the final folder, as mv's destination. The staged name
    # is exactly aurae, so a concurrent installation is skipped, never nested.
    # Stage and target share a filesystem; promotion does not copy partial files.
    mv -n -- "$AURAE_stage_dir/aurae" "$AURAE_skills_parent/" || aurae_die 'Could not install the staged package.'
    [[ ! -e $AURAE_stage_dir/aurae && ! -L $AURAE_stage_dir/aurae ]] ||
        aurae_die 'The destination appeared during installation. It was not overwritten.'
    [[ -d $AURAE_target && ! -L $AURAE_target ]] || aurae_die 'Cannot verify the installed folder.'
    AURAE_update_succeeded=1
    if [[ $AURAE_update -eq 1 ]]; then
        printf 'Updated AURAE from %s to %s at %s\n' "$installed_version" "$version" "$AURAE_target"
        printf 'Restart the agent, then run /AURAE upgrade to refresh the project state.\nBackup retained at %s\n' "$AURAE_backup_dir"
    else
        printf 'Installed AURAE %s locally at %s\n' "$version" "$AURAE_target"
        printf 'Review the installed skill and vendor profile, then start a new agent session.\n'
    fi
}

# Keep execution last so a truncated download cannot start a partial installer.
aurae_main "$@"
