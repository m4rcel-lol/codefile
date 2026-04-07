#!/usr/bin/env bash
set -euo pipefail

REPO="${CODEFILE_REPO:-m4rcel-lol/codefile}"
TAG="${CODEFILE_TAG:-latest}"
INSTALL_DIR="${CODEFILE_INSTALL_DIR:-/usr/local/bin}"
FALLBACK_INSTALL_DIR="${CODEFILE_FALLBACK_DIR:-${HOME}/.local/bin}"
BASHRC_FILE="${HOME}/.bashrc"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PATH_UPDATED=0
TMP_FILE=""

need_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Error: required command '$1' was not found." >&2
        exit 1
    fi
}

resolve_latest_tag() {
    local latest_url
    latest_url="$(curl -fsSLI -o /dev/null -w '%{url_effective}' "https://github.com/${REPO}/releases/latest")" || {
        echo "Error: unable to resolve latest release for ${REPO}." >&2
        return 1
    }

    local resolved_tag
    resolved_tag="$(basename "${latest_url}")"
    if [ -z "${resolved_tag}" ] || [ "${resolved_tag}" = "releases" ] || [ "${resolved_tag}" = "latest" ]; then
        echo "Error: no GitHub release tag found for ${REPO}. Place the 'codefile' binary next to this installer script and run it again." >&2
        return 1
    fi

    echo "${resolved_tag}"
}

download_binary() {
    local effective_tag="$1"
    local url="https://github.com/${REPO}/releases/download/${effective_tag}/codefile"
    local out="$2"

    echo "Downloading ${url} ..."
    curl -fsSL "${url}" -o "${out}"
    chmod +x "${out}"
}

find_local_binary() {
    local local_binary="${SCRIPT_DIR}/codefile"

    if [ ! -f "${local_binary}" ]; then
        return 1
    fi

    chmod +x "${local_binary}" 2>/dev/null || true
    echo "${local_binary}"
}

install_binary() {
    local src="$1"
    local chosen_dir="${INSTALL_DIR}"
    local target

    if [ ! -d "${chosen_dir}" ]; then
        mkdir -p "${chosen_dir}" 2>/dev/null || true
    fi

    target="${chosen_dir}/codefile"
    if [ -w "${chosen_dir}" ]; then
        install -m 0755 "${src}" "${target}"
        echo "${chosen_dir}"
        return 0
    fi

    if command -v sudo >/dev/null 2>&1; then
        sudo install -m 0755 "${src}" "${target}"
        echo "${chosen_dir}"
        return 0
    fi

    chosen_dir="${FALLBACK_INSTALL_DIR}"
    mkdir -p "${chosen_dir}"
    target="${chosen_dir}/codefile"
    install -m 0755 "${src}" "${target}"
    echo "${chosen_dir}"
}

ensure_bash_path() {
    local target_dir="$1"
    local export_line="export PATH=\"\$PATH:${target_dir}\""

    if [[ ":${PATH}:" == *":${target_dir}:"* ]]; then
        return 0
    fi

    if [ -f "${BASHRC_FILE}" ] && grep -Fq "${export_line}" "${BASHRC_FILE}"; then
        return 0
    fi

    if [ ! -f "${BASHRC_FILE}" ]; then
        touch "${BASHRC_FILE}"
    fi

    echo "${export_line}" >> "${BASHRC_FILE}"
    echo "Added ${target_dir} to PATH in ${BASHRC_FILE}"
    PATH_UPDATED=1
    return 0
}

cleanup_tmp() {
    if [ -n "${TMP_FILE}" ] && [ -f "${TMP_FILE}" ]; then
        rm -f "${TMP_FILE}"
    fi
}

main() {
    need_cmd install
    trap cleanup_tmp EXIT

    local source_binary
    if source_binary="$(find_local_binary)"; then
        echo "Using local binary: ${source_binary}"
    else
        need_cmd curl

        local effective_tag="${TAG}"
        if [ "${TAG}" = "latest" ]; then
            effective_tag="$(resolve_latest_tag)"
        fi

        TMP_FILE="$(mktemp)"
        source_binary="${TMP_FILE}"
        download_binary "${effective_tag}" "${source_binary}"
    fi

    local final_install_dir
    final_install_dir="$(install_binary "${source_binary}")"
    ensure_bash_path "${final_install_dir}"

    echo "Codefile installed to ${final_install_dir}/codefile"
    if [ "${PATH_UPDATED}" -eq 1 ]; then
        echo "Bash PATH updated. Restart Bash or run: source ${BASHRC_FILE}"
    fi
    "${final_install_dir}/codefile" version
}

main "$@"
